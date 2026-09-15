/* quiz.js — conclusão e atalhos de teclado do quiz */
document.addEventListener("DOMContentLoaded", function () {
    var endModal = document.getElementById("quiz-end-modal");
    if (endModal && typeof endModal.showModal === "function") {
        endModal.showModal();
    }

    var quizForm = document.querySelector(".quiz-form");
    if (!quizForm) {
        return;
    }

    document.addEventListener("keydown", function (event) {
        if (event.ctrlKey || event.metaKey || event.altKey) {
            return;
        }

        if (/^[0-6]$/.test(event.key)) {
            var option = quizForm.querySelector('input[name="resposta"][value="' + event.key + '"]');
            if (option) {
                option.checked = true;
                option.dispatchEvent(new Event("change", { bubbles: true }));
                event.preventDefault();
            }
            return;
        }

        if (event.key === "Enter") {
            var selected = quizForm.querySelector('input[name="resposta"]:checked');
            if (selected) {
                event.preventDefault();
                quizForm.requestSubmit();
            }
        }
    });
});
