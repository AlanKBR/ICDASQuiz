/* quiz.js — abre o modal de conclusão do quiz automaticamente */
document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById('quiz-end-modal');
    if (modal && typeof modal.showModal === 'function') {
        modal.showModal();
    }
});
