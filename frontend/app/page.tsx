export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-neutral-950 px-4 text-neutral-100">
      <main className="w-full max-w-2xl">
        <h1 className="mb-2 text-2xl font-medium">geomesh</h1>
        <p className="mb-12 text-sm text-neutral-500">
          turn locations into 3d meshes for games
        </p>

        <div className="mb-8 rounded border border-neutral-800 bg-neutral-900 p-8 text-center">
          <div className="mb-4 text-4xl text-neutral-600">[ ]</div>
          <p className="text-sm text-neutral-400">map interface coming soon</p>
          <p className="mt-1 text-xs text-neutral-600">
            leaflet integration next
          </p>
        </div>

        <div className="space-y-3 text-sm">
          <div className="flex gap-3">
            <span className="text-neutral-600">→</span>
            <div>
              <span className="text-neutral-300">select area on map</span>
              <span className="ml-2 text-neutral-600">draw rectangle</span>
            </div>
          </div>
          <div className="flex gap-3">
            <span className="text-neutral-600">→</span>
            <div>
              <span className="text-neutral-300">preview size</span>
              <span className="ml-2 text-neutral-600">1-5km validation</span>
            </div>
          </div>
          <div className="flex gap-3">
            <span className="text-neutral-600">→</span>
            <div>
              <span className="text-neutral-300">download .obj</span>
              <span className="ml-2 text-neutral-600">terrain + buildings</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
