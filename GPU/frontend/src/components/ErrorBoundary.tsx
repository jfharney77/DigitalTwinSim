import { Component, type ReactNode } from "react";

// spec_21 #8: a rendering crash in one tab shows a contained card instead of
// blanking the whole app. State is intentionally minimal — recovery is
// "switch tabs or reload", honestly stated.

export class ErrorBoundary extends Component<
  { label: string; children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="an-card">
          <h3>The {this.props.label} view hit an error</h3>
          <p className="mini">{String(this.state.error)}</p>
          <p className="mini">
            The rest of the app still works — switch tabs, or reload the page.
          </p>
          <button onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
