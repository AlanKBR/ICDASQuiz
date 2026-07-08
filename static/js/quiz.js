/* quiz.js — modal de conclusão */
document.addEventListener("DOMContentLoaded", function () {
    var endModal = document.getElementById("quiz-end-modal");
    if (endModal && typeof endModal.showModal === "function") {
        endModal.showModal();
    }
});
