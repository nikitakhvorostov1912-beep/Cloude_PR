export function BackgroundBlobs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Gradient base */}
      <div className="absolute inset-0 bg-gradient-to-br from-bg to-bg-alt" />

      {/* Blob 1 — indigo */}
      <div
        className="absolute w-[500px] h-[500px] rounded-full opacity-[0.07]"
        style={{
          background: 'radial-gradient(circle, #6C5CE7 0%, transparent 70%)',
          top: '10%',
          left: '15%',
          animation: 'blob-float-1 25s ease-in-out infinite',
        }}
      />

      {/* Blob 2 — teal */}
      <div
        className="absolute w-[400px] h-[400px] rounded-full opacity-[0.06]"
        style={{
          background: 'radial-gradient(circle, #00CEC9 0%, transparent 70%)',
          top: '50%',
          right: '10%',
          animation: 'blob-float-2 20s ease-in-out infinite',
        }}
      />

      {/* Blob 3 — light indigo */}
      <div
        className="absolute w-[350px] h-[350px] rounded-full opacity-[0.05]"
        style={{
          background: 'radial-gradient(circle, #A29BFE 0%, transparent 70%)',
          bottom: '10%',
          left: '40%',
          animation: 'blob-float-3 30s ease-in-out infinite',
        }}
      />

      {/* Blob 4 — warm accent */}
      <div
        className="absolute w-[300px] h-[300px] rounded-full opacity-[0.04]"
        style={{
          background: 'radial-gradient(circle, #FDCB6E 0%, transparent 70%)',
          top: '30%',
          left: '60%',
          animation: 'blob-float-2 35s ease-in-out infinite reverse',
        }}
      />
    </div>
  );
}
