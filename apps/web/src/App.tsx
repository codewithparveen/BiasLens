import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";

const LandingPage = lazy(() => import("@/pages/LandingPage").then((m) => ({ default: m.LandingPage })));
const ResultsPage = lazy(() => import("@/pages/ResultsPage").then((m) => ({ default: m.ResultsPage })));

export default function App() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </Suspense>
  );
}
