export default function PostPage({ params }: { params: { id: string } }) {
  return (
    <main className="container mx-auto p-8">
      <p className="text-gray-400">Post {params.id} em construção...</p>
    </main>
  );
}
