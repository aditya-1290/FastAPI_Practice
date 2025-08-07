// Minimal dashboard.js to handle ticket form submission

document.addEventListener('DOMContentLoaded', function() {
    const ticketForm = document.getElementById('ticketForm');
    if (ticketForm) {
        ticketForm.addEventListener('submit', async function(event) {
            event.preventDefault();

            const formData = new FormData(ticketForm);
            const data = {
                subject: formData.get('subject'),
                category: formData.get('category'),
                description: formData.get('description'),
                priority: formData.get('priority')
            };

            try {
                const response = await fetch('/create_ticket', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    alert('Ticket created successfully!');
                    ticketForm.reset();
                } else {
                    const errorData = await response.json();
                    alert('Error creating ticket: ' + (errorData.detail || 'Unknown error'));
                }
            } catch (error) {
                alert('Network error: ' + error.message);
            }
        });
    }
});
