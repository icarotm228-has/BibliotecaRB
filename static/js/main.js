// Scripts auxiliares: modal de confirmação, campos dinâmicos do cadastro e atalho de devolução.
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('confirm-modal');
  const texto = document.getElementById('confirm-text');
  let pendente = null;

  const abrir = (form) => {
    pendente = form;
    // {campo} no data-confirm é substituído pelo valor do campo do formulário
    texto.textContent = form.dataset.confirm.replace(/\{(\w+)\}/g, (_, n) => (form.elements[n] && form.elements[n].value) || '—');
    modal.classList.remove('hidden'); modal.classList.add('flex');
  };
  const fechar = () => { modal.classList.add('hidden'); modal.classList.remove('flex'); pendente = null; };

  document.querySelectorAll('form[data-confirm]').forEach((f) =>
    f.addEventListener('submit', (e) => { e.preventDefault(); abrir(f); }));
  document.getElementById('confirm-ok').addEventListener('click', () => { const f = pendente; fechar(); if (f) f.submit(); });
  document.getElementById('confirm-cancel').addEventListener('click', fechar);
  modal.addEventListener('click', (e) => { if (e.target === modal) fechar(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') fechar(); });

  // Cadastro de usuário: mostra os campos de aluno ou professor conforme o tipo
  const tipo = document.getElementById('tipo');
  if (tipo) {
    const alternar = () => {
      document.querySelectorAll('.campos-ALUNO').forEach((el) => el.classList.toggle('hidden', tipo.value !== 'ALUNO'));
      document.querySelectorAll('.campos-PROFESSOR').forEach((el) => el.classList.toggle('hidden', tipo.value !== 'PROFESSOR'));
    };
    tipo.addEventListener('change', alternar); alternar();
  }

  // Acervo: filtro em tempo real (título, autor, categoria ou tombo)
  const busca = document.getElementById('busca');
  if (busca) {
    const linhas = [...document.querySelectorAll('.linha-acervo')];
    busca.addEventListener('input', () => {
      const t = busca.value.trim().toLowerCase();
      linhas.forEach((l) => l.classList.toggle('hidden', t !== '' && !l.dataset.busca.includes(t)));
    });
  }

  // Devolução: botão "Devolver" preenche o campo de tombo
  document.querySelectorAll('[data-tombo]').forEach((b) =>
    b.addEventListener('click', () => { const i = document.getElementById('tombo'); i.value = b.dataset.tombo; i.focus(); window.scrollTo({ top: 0, behavior: 'smooth' }); }));
});
