"use client";

import { type ReactNode } from "react";
import { motion } from "framer-motion";
import { pageTransition } from "@/lib/motion";

interface PageWrapperProps {
  children: ReactNode;
  className?: string;
}

/**
 * PageWrapper — wraps page content with smooth entrance animation.
 * Uses spring-based fade + slide + blur transition.
 */
export function PageWrapper({ children, className }: PageWrapperProps) {
  return (
    <motion.div
      variants={pageTransition}
      initial="initial"
      animate="animate"
      className={className}
    >
      {children}
    </motion.div>
  );
}
