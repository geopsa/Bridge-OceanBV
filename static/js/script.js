function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (email && password) {
        alert('Login successful! (Demo)');
        // TODO: POST to /api/login
    } else {
        alert('Please fill in all fields');
    }
}

function handleRegister(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    if (username && email && password && confirmPassword) {
        if (password === confirmPassword) {
            alert('Registration successful! (Demo)');
            // TODO: POST to /api/register
        } else {
            alert('Passwords do not match');
        }
    } else {
        alert('Please fill in all fields');
    }
}


