import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/** Root component — just hosts the router. The Shell provides the layout. */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
