import { useState } from "react";
import Header from "./components/Header";
import RuleForm from "./components/RuleForm";
import ResultPanel from "./components/ResultPanel";

export interface InterpretResponse {
  intent: string | null;
  clarification_needed: { missing_fields: string[]; questions: string[] } | null;
  created_rule: Record<string, unknown> | null;
  dry_run: boolean;
}

export type AppState = "idle" | "loading" | "success" | "error";

function App() {
  const [result, setResult] = useState<InterpretResponse | null>(null);
  const [appState, setAppState] = useState<AppState>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");

  function handleResult(response: InterpretResponse) {
    setResult(response);
    setAppState("success");
    setErrorMessage("");
  }

  function handleError(message: string) {
    setResult(null);
    setAppState("error");
    setErrorMessage(message);
  }

  function handleLoading(loading: boolean) {
    if (loading) {
      setAppState("loading");
      setResult(null);
      setErrorMessage("");
    }
  }

  return (
    <div className="app">
      <Header />
      <main className="main-content">
        <RuleForm
          onResult={handleResult}
          onError={handleError}
          onLoading={handleLoading}
          isLoading={appState === "loading"}
        />
        {(appState === "success" || appState === "error") && (
          <ResultPanel
            result={result}
            errorMessage={errorMessage}
            hasError={appState === "error"}
          />
        )}
      </main>
    </div>
  );
}

export default App;
