// Página mínima de la etapa 1.0; el catálogo real llega en la etapa 1.6.
export default function Catalog() {
  return (
    <>
      <header className="bg-primary px-4 py-4">
        <img
          src="/marca/logo-horizontal-negativo.svg"
          alt="Suministros Hidráulicos Turmero"
          width={200}
          height={59}
          className="mx-auto h-auto w-50"
        />
      </header>
      <main className="mx-auto max-w-2xl p-4 text-center">
        <h1 className="mb-2 text-2xl font-bold">Suministros Hidráulicos Turmero</h1>
        <p className="mb-4">Mangueras hidráulicas, conexiones, ferrules y ferretería.</p>
        <p className="inline-block rounded-lg bg-accent px-3 py-2 font-semibold text-on-accent">
          Catálogo en construcción
        </p>
      </main>
    </>
  );
}
