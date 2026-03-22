export function BackgroundBlobs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Blob 1 — фиолетовый, верхний левый */}
      <div
        style={{
          position: 'absolute',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: '#7B6FE8',
          top: '-200px',
          left: '-100px',
          filter: 'blur(100px)',
          opacity: 0.55,
          animation: 'blob-float-1 25s ease-in-out infinite',
        }}
      />

      {/* Blob 2 — голубой, нижний правый */}
      <div
        style={{
          position: 'absolute',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background: '#38BDF8',
          bottom: '-150px',
          right: '-100px',
          filter: 'blur(90px)',
          opacity: 0.45,
          animation: 'blob-float-2 20s ease-in-out infinite',
        }}
      />

      {/* Blob 3 — пурпурный, центр-право */}
      <div
        style={{
          position: 'absolute',
          width: '400px',
          height: '400px',
          borderRadius: '50%',
          background: '#C084FC',
          top: '30%',
          right: '20%',
          filter: 'blur(110px)',
          opacity: 0.35,
          animation: 'blob-float-3 30s ease-in-out infinite',
        }}
      />
    </div>
  );
}
