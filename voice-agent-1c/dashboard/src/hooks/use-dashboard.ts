"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi, healthApi, voicesApi } from "@/lib/api";

export function useDashboardSummary(period: number) {
  return useQuery({
    queryKey: ["dashboard", "summary", period],
    queryFn: () => dashboardApi.summary(period),
    refetchInterval: 30_000,
  });
}

export function useDashboardCalls(params: {
  period: number;
  limit: number;
  offset: number;
}) {
  return useQuery({
    queryKey: ["dashboard", "calls", params],
    queryFn: () => dashboardApi.calls(params),
  });
}

export function useDashboardDepartments(period: number) {
  return useQuery({
    queryKey: ["dashboard", "departments", period],
    queryFn: () => dashboardApi.departments(period),
    refetchInterval: 30_000,
  });
}

export function useCallDetail(callId: string) {
  return useQuery({
    queryKey: ["call", callId],
    queryFn: () => dashboardApi.callDetail(callId),
    enabled: !!callId,
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => healthApi.check(),
    refetchInterval: 10_000,
    retry: false,
  });
}

export function useVoices() {
  return useQuery({
    queryKey: ["voices"],
    queryFn: () => voicesApi.list(),
  });
}
