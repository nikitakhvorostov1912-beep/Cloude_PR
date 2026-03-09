"use client";

import { DotNav } from "./components/dot-nav";
import { SectionHero } from "./components/section-hero";
import { SectionProblem } from "./components/section-problem";
import { SectionSolution } from "./components/section-solution";
import { SectionLiveDemo } from "./components/section-live-demo";
import { SectionCallFlow } from "./components/section-call-flow";
import { SectionScenarios } from "./components/section-scenarios";
import { SectionArchitecture } from "./components/section-architecture";
import { SectionROI } from "./components/section-roi";
import { SectionRoadmap } from "./components/section-roadmap";
import { SectionCases } from "./components/section-cases";
import { SectionCTA } from "./components/section-cta";

export default function PitchPage() {
  return (
    <>
      <DotNav />
      <div className="relative">
        <SectionHero />
        <SectionProblem />
        <SectionSolution />
        <SectionLiveDemo />
        <SectionCallFlow />
        <SectionScenarios />
        <SectionArchitecture />
        <SectionROI />
        <SectionRoadmap />
        <SectionCases />
        <SectionCTA />
      </div>
    </>
  );
}
