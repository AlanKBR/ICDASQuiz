/* quiz.js — modais de conclusão e de nome */
document.addEventListener('DOMContentLoaded', function () {
    // ── Modal de conclusão do quiz ──────────────────────────────────────
    var endModal = document.getElementById('quiz-end-modal');
    if (endModal && typeof endModal.showModal === 'function') {
        endModal.showModal();
    }

    // ── Modal de inserção de nome ───────────────────────────────────────
    var nomeModal   = document.getElementById('nome-modal');
    var nomeInput   = document.getElementById('nome-input');
    var btnSalvar        = document.getElementById('btn-salvar');
    var btnSalvarCompl   = document.getElementById('btn-salvar-completar');
    var btnCancelar      = document.getElementById('nome-cancelar');

    function abrirNomeModal() {
        if (nomeModal && typeof nomeModal.showModal === 'function') {
            nomeModal.showModal();
            if (nomeInput) { nomeInput.focus(); }
        }
    }

    if (btnSalvar)      { btnSalvar.addEventListener('click', abrirNomeModal); }
    if (btnSalvarCompl) { btnSalvarCompl.addEventListener('click', abrirNomeModal); }

    if (btnCancelar) {
        btnCancelar.addEventListener('click', function () {
            nomeModal.close();
        });
    }

    // Fechar ao clicar fora do article (backdrop click)
    if (nomeModal) {
        nomeModal.addEventListener('click', function (e) {
            if (e.target === nomeModal) { nomeModal.close(); }
        });
    }
});
