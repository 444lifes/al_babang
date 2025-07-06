document.addEventListener('DOMContentLoaded', () => {
    const alumniSearch = document.getElementById('alumniSearch');
    const alumniFilterYear = document.getElementById('alumniFilterYear');
    const alumniResults = document.getElementById('alumniResults');

    const allAlumniCards = alumniResults ? alumniResults.querySelectorAll('.alumni-card') : [];

    function filterAlumni() {
        const searchText = alumniSearch.value.toLowerCase();
        const filterYear = alumniFilterYear.value;

        allAlumniCards.forEach(card => {
            const alumniName = card.querySelector('h3').textContent.toLowerCase();
            const angkatanLulus = card.dataset.angkatan;

            const matchesSearch = alumniName.includes(searchText);
            const matchesFilter = filterYear === '' || angkatanLulus === filterYear;

            if (matchesSearch && matchesFilter) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    if (alumniSearch) {
        alumniSearch.addEventListener('keyup', filterAlumni);
    }
    if (alumniFilterYear) {
        alumniFilterYear.addEventListener('change', filterAlumni);
    }
});