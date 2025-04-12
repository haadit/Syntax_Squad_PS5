// Supabase client configuration
const supabaseUrl = 'https://mabduayfrbwgqzqtkkgu.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hYmR1YXlmcmJ3Z3F6cXRra2d1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ0MTQ0MDIsImV4cCI6MjA1OTk5MDQwMn0.NShOA-EpM3WTs7wSZe5z4-4I64b56UmlYKde5E_8Rvo';
const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);



// Authentication state
let currentUser = null;

// DOM Elements
const authContainer = document.getElementById('auth-container');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const logoutButton = document.getElementById('logout-button');
const userInfo = document.getElementById('user-info');

// Check if user is logged in
async function checkAuth() {
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
        currentUser = session.user;
        showAuthenticatedUI();
    } else {
        showUnauthenticatedUI();
    }
}

// Register new user
async function register(email, password) {
    try {
        const { data, error } = await supabase.auth.signUp({
            email,
            password
        });
        
        if (error) throw error;
        
        showMessage('Registration successful! Please check your email for verification.', 'success');
        showLoginForm();
    } catch (error) {
        showMessage(error.message, 'error');
    }
}

// Login user
async function login(email, password) {
    try {
        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password
        });
        
        if (error) throw error;
        
        currentUser = data.user;
        showAuthenticatedUI();
        showMessage('Login successful!', 'success');
    } catch (error) {
        showMessage(error.message, 'error');
    }
}

// Logout user
async function logout() {
    try {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;
        
        currentUser = null;
        showUnauthenticatedUI();
        showMessage('Logged out successfully', 'success');
    } catch (error) {
        showMessage(error.message, 'error');
    }
}

// UI Functions
function showAuthenticatedUI() {
    authContainer.style.display = 'none';
    userInfo.style.display = 'block';
    logoutButton.style.display = 'block';
    document.getElementById('user-email').textContent = currentUser.email;
}

function showUnauthenticatedUI() {
    authContainer.style.display = 'block';
    userInfo.style.display = 'none';
    logoutButton.style.display = 'none';
}

function showLoginForm() {
    document.getElementById('register-form').style.display = 'none';
    document.getElementById('login-form').style.display = 'block';
}

function showRegisterForm() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('auth-message');
    messageDiv.textContent = message;
    messageDiv.className = `p-4 rounded ${type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    
    // Login form
    loginForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        await login(email, password);
    });
    
    // Register form
    registerForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        await register(email, password);
    });
    
    // Logout button
    logoutButton?.addEventListener('click', logout);
}); 