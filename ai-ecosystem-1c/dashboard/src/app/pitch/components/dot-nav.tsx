"use client";

import { useState, useEffect, useCallback } from "react";

const SECTIONS = [
  { id: "hero", label: "Начало" },
  { id: "problem", label: "Проблема" },
  { id: "solution", label: "Решение" },
  { id: "live-demo", label: "Live Demo" },
  { id: "call-flow", label: "Процесс" },
  { id: "scenarios", label: "Сценарии" },
  { id: "architecture", label: "Архитектура" },
  { id: "roi", label: "ROI" },
  { id: "roadmap", label: "Дорожная карта" },
  { id: "cases", label: "Кейсы" },
  { id: "cta", label: "Старт" },
];

export function DotNav() {
  const [activeId, setActiveId] = useState("hero");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { threshold: 0.4 }
    );

    for (const section of SECTIONS) {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, []);

  const scrollTo = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  return (
    <nav className="dot-nav">
      {SECTIONS.map((section) => (
        <button
          key={section.id}
          onClick={() => scrollTo(section.id)}
          className={`dot-nav-item ${activeId === section.id ? "active" : ""}`}
          aria-label={section.label}
        >
          <span className="dot-nav-label">{section.label}</span>
        </button>
      ))}
    </nav>
  );
}
