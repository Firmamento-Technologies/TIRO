import { useParams } from 'react-router-dom';

export function TiroSoggettoDettaglioPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div style={{ padding: 24, color: '#F8FAFC' }}>
      <h1>Soggetto #{id}</h1>
      <p>Coming soon...</p>
    </div>
  );
}

export const Component = TiroSoggettoDettaglioPage;
