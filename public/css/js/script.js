document.addEventListener('DOMContentLoaded', () => {
    const registrationForm = document.getElementById('registrationForm');
    const confirmationMessage = document.getElementById('confirmationMessage');

    if (registrationForm) {
        registrationForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const formData = new FormData(registrationForm);

            // Client-side validation for file size and type
            const files = ['ktpOrtu', 'kk', 'dataCalon'];
            for (const fileInputName of files) {
                const fileInput = document.getElementById(fileInputName);
                if (fileInput && fileInput.files.length > 0) {
                    const file = fileInput.files[0];
                    if (file.size > 500 * 1024) { // 500 KB
                        alert(`Ukuran file ${file.name} melebihi batas maksimal 500 KB.`);
                        return;
                    }
                    if (file.type !== 'image/jpeg') {
                        alert(`File ${file.name} harus dalam format JPG.`);
                        return;
                    }
                }
            }

            try {
                // Here you would send the formData to your backend server
                // Example using fetch API:
                const response = await fetch('/api/pendaftaran', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    registrationForm.reset(); // Clear the form
                    registrationForm.style.display = 'none';
                    confirmationMessage.style.display = 'block';
                } else {
                    const errorData = await response.json();
                    alert(`Pendaftaran gagal: ${errorData.message || 'Terjadi kesalahan.'}`);
                }
            } catch (error) {
                console.error('Error during registration:', error);
                alert('Terjadi kesalahan saat mengirim pendaftaran. Mohon coba lagi.');
            }
        });
    }
});