document.querySelectorAll('.hover-scale').forEach((card) => {
  card.addEventListener('mousemove', () => card.classList.add('ring-2', 'ring-cyan-300/50'));
  card.addEventListener('mouseleave', () => card.classList.remove('ring-2', 'ring-cyan-300/50'));
});
