export default function StatusBadge({status}) {
  const value = status || 'PENDING';
  return (
    <span className={`status status-${value.toLowerCase()}`}>
      <i /> {value}
    </span>
  );
}
