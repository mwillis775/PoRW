/**
 * JavaScript for controlling mining and storage nodes.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mining node controls
    const startMiningForm = document.querySelector('form[action="/mining/start"]');
    if (startMiningForm) {
        startMiningForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(startMiningForm);
            
            // Send POST request to start mining
            fetch('/mining/start', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success';
                    alert.innerHTML = `<strong>Success!</strong> ${data.message}`;
                    startMiningForm.parentNode.insertBefore(alert, startMiningForm);
                    
                    // Reload the page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    // Show error message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-danger';
                    alert.innerHTML = `<strong>Error!</strong> ${data.message}`;
                    startMiningForm.parentNode.insertBefore(alert, startMiningForm);
                }
            })
            .catch(error => {
                console.error('Error starting mining node:', error);
                
                // Show error message
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger';
                alert.innerHTML = '<strong>Error!</strong> Failed to start mining node.';
                startMiningForm.parentNode.insertBefore(alert, startMiningForm);
            });
        });
    }
    
    // Stop mining form
    const stopMiningForm = document.querySelector('form[action="/mining/stop"]');
    if (stopMiningForm) {
        stopMiningForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Send POST request to stop mining
            fetch('/mining/stop', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success';
                    alert.innerHTML = `<strong>Success!</strong> ${data.message}`;
                    stopMiningForm.parentNode.insertBefore(alert, stopMiningForm);
                    
                    // Reload the page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    // Show error message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-danger';
                    alert.innerHTML = `<strong>Error!</strong> ${data.message}`;
                    stopMiningForm.parentNode.insertBefore(alert, stopMiningForm);
                }
            })
            .catch(error => {
                console.error('Error stopping mining node:', error);
                
                // Show error message
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger';
                alert.innerHTML = '<strong>Error!</strong> Failed to stop mining node.';
                stopMiningForm.parentNode.insertBefore(alert, stopMiningForm);
            });
        });
    }
    
    // Storage node controls
    const startStorageForm = document.querySelector('form[action="/storage/start"]');
    if (startStorageForm) {
        startStorageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(startStorageForm);
            
            // Send POST request to start storage node
            fetch('/storage/start', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success';
                    alert.innerHTML = `<strong>Success!</strong> ${data.message}`;
                    startStorageForm.parentNode.insertBefore(alert, startStorageForm);
                    
                    // Reload the page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    // Show error message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-danger';
                    alert.innerHTML = `<strong>Error!</strong> ${data.message}`;
                    startStorageForm.parentNode.insertBefore(alert, startStorageForm);
                }
            })
            .catch(error => {
                console.error('Error starting storage node:', error);
                
                // Show error message
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger';
                alert.innerHTML = '<strong>Error!</strong> Failed to start storage node.';
                startStorageForm.parentNode.insertBefore(alert, startStorageForm);
            });
        });
    }
    
    // Stop storage form
    const stopStorageForm = document.querySelector('form[action="/storage/stop"]');
    if (stopStorageForm) {
        stopStorageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Send POST request to stop storage node
            fetch('/storage/stop', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success';
                    alert.innerHTML = `<strong>Success!</strong> ${data.message}`;
                    stopStorageForm.parentNode.insertBefore(alert, stopStorageForm);
                    
                    // Reload the page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    // Show error message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-danger';
                    alert.innerHTML = `<strong>Error!</strong> ${data.message}`;
                    stopStorageForm.parentNode.insertBefore(alert, stopStorageForm);
                }
            })
            .catch(error => {
                console.error('Error stopping storage node:', error);
                
                // Show error message
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger';
                alert.innerHTML = '<strong>Error!</strong> Failed to stop storage node.';
                stopStorageForm.parentNode.insertBefore(alert, stopStorageForm);
            });
        });
    }
});
