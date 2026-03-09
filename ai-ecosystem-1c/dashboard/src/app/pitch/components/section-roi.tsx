"use client";

import { useRef, useState, useMemo } from "react";
import { motion, useInView } from "framer-motion";
import { Calculator, Clock, Banknote, PhoneIncoming, TrendingUp, CalendarCheck } from "lucide-react";
import { GlowCard } from "@/components/glow-card";
import { AnimatedCounter } from "@/components/animated-counter";

const IMPLEMENTATION_COST = 2_500_000; // 2.5M rub
const HOURLY_RATE = 500; // rub per hour per operator
const TARGET_TIME_MIN = 4; // target AHT after Аврора
const WORK_DAYS = 22; // per month

export function SectionROI() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const [operators, setOperators] = useState(15);
  const [callsPerDay, setCallsPerDay] = useState(20);
  const [currentAHT, setCurrentAHT] = useState(12);

  const metrics = useMemo(() => {
    const timeSavedMinPerDay = operators * callsPerDay * (currentAHT - TARGET_TIME_MIN);
    const timeSavedHoursPerMonth = (timeSavedMinPerDay * WORK_DAYS) / 60;
    const moneySavedPerMonth = timeSavedHoursPerMonth * HOURLY_RATE;
    const extraCallsPerMonth = Math.floor(timeSavedHoursPerMonth * (60 / TARGET_TIME_MIN));
    const annualSaving = moneySavedPerMonth * 12;
    const roi = Math.round(((annualSaving - IMPLEMENTATION_COST) / IMPLEMENTATION_COST) * 100);
    const paybackMonths = moneySavedPerMonth > 0
      ? Math.ceil(IMPLEMENTATION_COST / moneySavedPerMonth)
      : 99;

    return {
      timeSavedHoursPerMonth: Math.round(timeSavedHoursPerMonth),
      moneySavedPerMonth: Math.round(moneySavedPerMonth),
      extraCallsPerMonth,
      roi,
      paybackMonths,
    };
  }, [operators, callsPerDay, currentAHT]);

  const RESULTS = [
    {
      icon: Clock,
      label: "Экономия времени",
      value: metrics.timeSavedHoursPerMonth,
      suffix: " ч/мес",
      color: "text-is-blue",
    },
    {
      icon: Banknote,
      label: "Экономия",
      value: Math.round(metrics.moneySavedPerMonth / 1000),
      prefix: "₽",
      suffix: "K/мес",
      color: "text-success",
    },
    {
      icon: PhoneIncoming,
      label: "Доп. звонки",
      value: metrics.extraCallsPerMonth,
      prefix: "+",
      suffix: "/мес",
      color: "text-aurora-purple",
    },
    {
      icon: TrendingUp,
      label: "ROI за год",
      value: metrics.roi,
      suffix: "%",
      color: "text-warning",
    },
    {
      icon: CalendarCheck,
      label: "Окупаемость",
      value: metrics.paybackMonths,
      suffix: " мес",
      color: "text-is-blue-light",
    },
  ];

  return (
    <section id="roi" className="pitch-section">
      <div ref={ref} className="pitch-section-inner">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="mb-12 text-center"
        >
          <h2 className="mb-3 text-4xl font-bold text-text-primary">
            ROI-калькулятор
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            Рассчитайте экономию для вашего call-центра
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.15 }}
          className="mx-auto max-w-4xl"
        >
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Inputs */}
            <GlowCard className="p-6">
              <div className="mb-1 flex items-center gap-2">
                <Calculator className="h-5 w-5 text-is-blue" />
                <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                  Параметры
                </h3>
              </div>
              <p className="mb-6 text-xs text-text-muted">
                Стоимость внедрения: ₽2.5M (MVP, 8 недель)
              </p>

              <div className="space-y-6">
                {/* Operators */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm text-text-secondary">
                      Количество операторов
                    </label>
                    <span className="font-mono text-sm font-semibold text-is-blue">
                      {operators}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={5}
                    max={50}
                    value={operators}
                    onChange={(e) => setOperators(Number(e.target.value))}
                  />
                  <div className="mt-1 flex justify-between text-xs text-text-muted">
                    <span>5</span>
                    <span>50</span>
                  </div>
                </div>

                {/* Calls per day */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm text-text-secondary">
                      Звонков в день на оператора
                    </label>
                    <span className="font-mono text-sm font-semibold text-is-blue">
                      {callsPerDay}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={40}
                    value={callsPerDay}
                    onChange={(e) => setCallsPerDay(Number(e.target.value))}
                  />
                  <div className="mt-1 flex justify-between text-xs text-text-muted">
                    <span>10</span>
                    <span>40</span>
                  </div>
                </div>

                {/* Current AHT */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm text-text-secondary">
                      Текущее ср. время обработки (мин)
                    </label>
                    <span className="font-mono text-sm font-semibold text-is-blue">
                      {currentAHT}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={6}
                    max={20}
                    value={currentAHT}
                    onChange={(e) => setCurrentAHT(Number(e.target.value))}
                  />
                  <div className="mt-1 flex justify-between text-xs text-text-muted">
                    <span>6 мин</span>
                    <span>20 мин</span>
                  </div>
                </div>
              </div>
            </GlowCard>

            {/* Results */}
            <div className="space-y-3">
              {RESULTS.map((result) => (
                <GlowCard key={result.label} className="p-4">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-bg-elevated">
                      <result.icon className={`h-5 w-5 ${result.color}`} />
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-text-muted">{result.label}</p>
                      <div className="flex items-baseline gap-1">
                        {result.prefix && (
                          <span className="text-lg font-bold text-text-primary">
                            {result.prefix}
                          </span>
                        )}
                        {isInView && (
                          <AnimatedCounter
                            value={result.value}
                            className="text-lg font-bold text-text-primary"
                          />
                        )}
                        <span className="text-sm text-text-secondary">
                          {result.suffix}
                        </span>
                      </div>
                    </div>
                  </div>
                </GlowCard>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
