"use client";

import { motion } from "framer-motion";

/**
 * AuroraBackground — animated aurora gradient blobs.
 * Dark Navy version with higher opacity for dark background.
 * 4 blobs: navy, red, blue, purple — drifting slowly.
 */
export function AuroraBackground() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 2.5, ease: "easeOut" }}
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
      aria-hidden="true"
    >
      <div className="aurora-blob aurora-blob-1" />
      <div className="aurora-blob aurora-blob-2" />
      <div className="aurora-blob aurora-blob-3" />
      <div className="aurora-blob aurora-blob-4" />
    </motion.div>
  );
}
