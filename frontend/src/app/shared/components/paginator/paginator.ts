import { Component, computed, input, output } from '@angular/core';

/** Page sizes offered in the dropdown. */
const PAGE_SIZES = [10, 20, 50];

/**
 * Pager for any list endpoint. Driven by the `Page<T>` fields the API returns
 * (`page`, `size`, `total`, `pages`) and emits the new value on change — the
 * parent owns the state and does the reloading.
 */
@Component({
  selector: 'app-paginator',
  template: `
    <div class="paginator">
      <span class="muted range">
        @if (total() === 0) {
          No results
        } @else {
          Showing {{ firstRow() }}–{{ lastRow() }} of {{ total() }}
        }
      </span>

      <span class="controls">
        <label class="size">
          Rows
          <select [value]="size()" (change)="onSize($event)">
            @for (option of sizes; track option) {
              <option [value]="option">{{ option }}</option>
            }
          </select>
        </label>

        <button class="btn" type="button" [disabled]="page() <= 1" (click)="go(page() - 1)">
          Previous
        </button>
        <span class="muted">Page {{ page() }} of {{ pages() || 1 }}</span>
        <button
          class="btn"
          type="button"
          [disabled]="page() >= pages()"
          (click)="go(page() + 1)"
        >
          Next
        </button>
      </span>
    </div>
  `,
  styles: `
    .paginator {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--space-3);
      margin-top: var(--space-4);
      font-size: 14px;
    }
    .controls {
      display: flex;
      align-items: center;
      gap: var(--space-3);
    }
    .size {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      color: var(--color-text-muted);
    }
    select {
      padding: 2px var(--space-2);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-surface);
      color: var(--color-text);
      font: inherit;
    }
  `,
})
export class Paginator {
  readonly page = input.required<number>();
  readonly size = input.required<number>();
  readonly total = input.required<number>();
  readonly pages = input.required<number>();

  readonly pageChange = output<number>();
  readonly sizeChange = output<number>();

  protected readonly sizes = PAGE_SIZES;

  protected readonly firstRow = computed(() => (this.page() - 1) * this.size() + 1);
  protected readonly lastRow = computed(() =>
    Math.min(this.page() * this.size(), this.total()),
  );

  protected go(page: number): void {
    this.pageChange.emit(page);
  }

  protected onSize(event: Event): void {
    this.sizeChange.emit(Number((event.target as HTMLSelectElement).value));
  }
}
