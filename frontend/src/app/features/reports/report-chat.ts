import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { Report } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { ChatMessage, ReportChatService } from './report-chat.service';

/** Both caps mirror the shipped backend contract (ChatRequest: maxLength 4000, history 20). */
const MAX_MESSAGE_LENGTH = 4000;
const MAX_HISTORY = 20;

/**
 * Ask questions about a report.
 *
 * The panel is complete, but the backend endpoint it needs does not exist yet.
 * `ReportChatService.isAvailable()` probes the API's OpenAPI document, so this
 * turns itself on the moment `POST /reports/{id}/chat` ships — no code change.
 */
@Component({
  selector: 'app-report-chat',
  imports: [ReactiveFormsModule],
  templateUrl: './report-chat.html',
  styleUrl: './report-chat.scss',
})
export class ReportChat implements OnInit {
  readonly report = input.required<Report>();

  private readonly chat = inject(ReportChatService);
  private readonly fb = inject(FormBuilder);

  protected readonly available = signal<boolean | null>(null); // null = still probing
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly sending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly maxLength = MAX_MESSAGE_LENGTH;

  /**
   * A FormGroup, not a bare FormControl, because `(ngSubmit)` is an output of
   * the FormGroupDirective — not a DOM event. A `<form>` with no `[formGroup]`
   * has no directive attached, so ngSubmit would never fire and pressing Enter
   * or clicking Ask would silently do nothing.
   */
  protected readonly form = this.fb.nonNullable.group({
    message: ['', [Validators.required, Validators.maxLength(MAX_MESSAGE_LENGTH)]],
  });

  /** Starter questions, so the panel is not a blank box. */
  protected readonly suggestions = [
    'Summarise the key differences in two sentences.',
    'What does the report say that is not backed by a citation?',
    'Which claim has the strongest supporting evidence?',
  ];

  ngOnInit(): void {
    // Disabled until we know the endpoint exists.
    this.form.disable();

    this.chat.isAvailable().subscribe((available) => {
      this.available.set(available);
      // Reactive forms own their disabled state — a `[disabled]` binding in the
      // template is ignored by the form directive, so toggle it here.
      if (available) {
        this.form.enable();
      } else {
        this.form.disable();
      }
    });
  }

  protected use(suggestion: string): void {
    this.form.controls.message.setValue(suggestion);
  }

  protected send(): void {
    if (this.form.invalid || this.sending()) {
      this.form.markAllAsTouched();
      return;
    }

    const question = this.form.getRawValue().message.trim();
    if (!question) {
      return;
    }

    // History is what preceded this question — the API is stateless, so we
    // replay it, trimmed to the most recent turns.
    const history = this.messages().slice(-MAX_HISTORY);

    this.messages.update((list) => [...list, { role: 'user', content: question }]);
    this.form.controls.message.setValue('');
    this.sending.set(true);
    this.error.set(null);

    this.chat.send(this.report().id, question, history).subscribe({
      next: (reply) => {
        this.messages.update((list) => [
          ...list,
          {
            role: 'assistant',
            content: reply.answer,
            citations: reply.citations ?? [],
            grounded: reply.grounded ?? true,
          },
        ]);
        this.sending.set(false);
      },
      error: (err) => {
        // Show the backend's own words. It answers 404 for an unknown report and
        // 503 when the language model is down — and deliberately does NOT fall
        // back to a made-up answer, so surfacing the real reason matters.
        const message = apiErrorMessage(err);
        this.error.set(message);
        this.messages.update((list) => [
          ...list,
          { role: 'assistant', content: message, failed: true },
        ]);
        this.sending.set(false);
      },
    });
  }

  protected clear(): void {
    this.messages.set([]);
    this.error.set(null);
  }
}
