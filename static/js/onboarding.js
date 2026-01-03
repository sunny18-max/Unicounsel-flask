// Enhanced Onboarding JavaScript with Voice Recognition

// Questions data
const questions = [
    {
        id: 'nationality',
        text: "What is your nationality?",
        placeholder: "e.g., Indian, American, Chinese",
        required: true
    },
    {
        id: 'qualification',
        text: "What is your highest qualification?",
        options: ['10th', '12th', 'Undergraduate', 'Postgraduate'],
        required: true
    },
    {
        id: 'marks',
        text: "What are your marks or CGPA?",
        placeholder: "e.g., 85% or 8.5 CGPA",
        required: true
    },
    {
        id: 'field',
        text: "What field or subjects are you interested in?",
        placeholder: "e.g., Computer Science, Business, Medicine",
        required: true
    },
    {
        id: 'budget',
        text: "What is your budget range per year for tuition and living expenses?",
        placeholder: "e.g., $20,000 - $40,000",
        required: true
    },
    {
        id: 'english',
        text: "Do you have an English proficiency score like IELTS or TOEFL?",
        placeholder: "e.g., IELTS 7.0, TOEFL 100, or None",
        required: false
    },
    {
        id: 'countries',
        text: "Which countries do you prefer to study in?",
        placeholder: "e.g., USA, UK, Canada, Australia, Germany",
        required: false
    },
    {
        id: 'gaps',
        text: "Do you have any gap years in your education?",
        placeholder: "e.g., 0, 1, 2 years",
        required: false
    },
    {
        id: 'career_goals',
        text: "What are your career aspirations after completing your education?",
        placeholder: "e.g., Work in tech industry, Start my own business, Research",
        required: true
    },
    {
        id: 'study_preference',
        text: "What type of learning environment do you prefer?",
        options: ['Practical/Hands-on', 'Theoretical/Research-based', 'Mixed'],
        required: true
    },
    {
        id: 'scholarship',
        text: "Are you interested in scholarship opportunities?",
        options: ['Yes', 'No', 'Maybe'],
        required: true
    },
    {
        id: 'timeline',
        text: "When are you planning to start your studies?",
        options: ['Within 6 months', '6-12 months', '1-2 years', 'Not sure yet'],
        required: true
    }
];

// Suggested answers
const suggestedAnswers = {
    field: ['Computer Science', 'Business Administration', 'Engineering', 'Medicine', 'Data Science', 'Psychology', 'Law', 'Arts & Design'],
    budget: ['$10,000 - $20,000', '$20,000 - $40,000', '$40,000 - $60,000', '$60,000+'],
    countries: ['USA', 'UK', 'Canada', 'Australia', 'Germany', 'Netherlands', 'Ireland', 'New Zealand'],
    english: ['IELTS 6.5', 'IELTS 7.0', 'IELTS 7.5', 'TOEFL 90', 'TOEFL 100', 'None'],
    gaps: ['0 years', '1 year', '2 years', '3+ years'],
    nationality: ['Indian', 'Chinese', 'Nigerian', 'Pakistani', 'Bangladeshi', 'Vietnamese', 'Other'],
    marks: ['60-70%', '70-80%', '80-90%', '90%+', '6.0-7.0 CGPA', '7.0-8.0 CGPA', '8.0+ CGPA']
};

// State
let currentQuestionIndex = 0;
let answers = {};
let recognition = null;
let isListening = false;
let synth = window.speechSynthesis;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeParticles();
    initializeVoiceRecognition();
    setupEventListeners();
});

// Particle System
function initializeParticles() {
    const canvas = document.getElementById('particleCanvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    const particleCount = 100;
    
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 1;
            this.speedX = Math.random() * 2 - 1;
            this.speedY = Math.random() * 2 - 1;
            this.opacity = Math.random() * 0.5 + 0.2;
            this.color = Math.random() > 0.5 ? 'rgba(0, 217, 255, ' : 'rgba(14, 165, 233, ';
        }
        
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            
            if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
            if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
        }
        
        draw() {
            ctx.fillStyle = this.color + this.opacity + ')';
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

// Voice Recognition
function initializeVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            document.getElementById('textInput').value = transcript;
            updateNextButton();
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            stopListening();
        };
        
        recognition.onend = () => {
            if (isListening) {
                recognition.start();
            }
        };
    }
}

function startListening() {
    if (recognition && !isListening) {
        recognition.start();
        isListening = true;
        document.getElementById('voiceBtn').classList.add('active');
        document.getElementById('voiceStatus').style.display = 'block';
        updateStatus('listening');
    }
}

function stopListening() {
    if (recognition && isListening) {
        recognition.stop();
        isListening = false;
        document.getElementById('voiceBtn').classList.remove('active');
        document.getElementById('voiceStatus').style.display = 'none';
        updateStatus('idle');
    }
}

function speak(text) {
    if (synth) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.9;
        utterance.pitch = 1;
        utterance.volume = 1;
        synth.speak(utterance);
        updateStatus('speaking');
        
        utterance.onend = () => {
            updateStatus('idle');
        };
    }
}

function updateStatus(status) {
    const indicator = document.getElementById('statusIndicator');
    indicator.className = `status-indicator ${status}`;
    
    const statusTexts = {
        'idle': 'Ready',
        'listening': 'Listening...',
        'speaking': 'Speaking...',
        'processing': 'Processing...'
    };
    
    indicator.querySelector('.status-text').textContent = statusTexts[status] || 'Ready';
}

// Event Listeners
function setupEventListeners() {
    // Start onboarding
    document.getElementById('startOnboarding').addEventListener('click', () => {
        showScreen('onboardingScreen');
        loadQuestion(0);
    });
    
    // Voice button
    document.getElementById('voiceBtn').addEventListener('click', () => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    });
    
    // Text input
    document.getElementById('textInput').addEventListener('input', () => {
        updateNextButton();
    });
    
    // Next button
    document.getElementById('nextBtn').addEventListener('click', () => {
        handleNextQuestion();
    });
    
    // Skip button
    document.getElementById('skipBtn').addEventListener('click', () => {
        handleSkip();
    });
    
    // Retake button - redirect to onboarding page (which will check if already completed)
    document.getElementById('retakeBtn').addEventListener('click', () => {
        // Clear onboarding data first
        fetch('/api/onboarding/clear', { method: 'POST' })
        .then(() => {
            window.location.href = '/onboarding';
        })
        .catch(() => {
            window.location.href = '/onboarding';
        });
    });
    
    // Go to dashboard
    document.getElementById('goToDashboardBtn').addEventListener('click', () => {
        // Save onboarding first, then redirect
        saveOnboardingAnswers().then(() => {
            window.location.href = '/dashboard';
        }).catch(() => {
            // Even if save fails, redirect to dashboard
            window.location.href = '/dashboard';
        });
    });
    
    // Enter key on input
    document.getElementById('textInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !document.getElementById('nextBtn').disabled) {
            handleNextQuestion();
        }
    });
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

function loadQuestion(index) {
    if (index >= questions.length) {
        processAnswers();
        return;
    }
    
    currentQuestionIndex = index;
    const question = questions[index];
    
    // Update progress
    const progress = ((index + 1) / questions.length) * 100;
    document.getElementById('currentQuestionNum').textContent = index + 1;
    document.getElementById('totalQuestions').textContent = questions.length;
    document.getElementById('progressPercent').textContent = Math.round(progress);
    document.getElementById('progressBar').style.width = progress + '%';
    
    // Update question
    document.getElementById('questionText').textContent = question.text;
    
    // Clear previous inputs
    document.getElementById('textInput').value = '';
    document.getElementById('textInputGroup').style.display = question.options ? 'none' : 'flex';
    document.getElementById('optionsGroup').innerHTML = '';
    document.getElementById('suggestedOptions').innerHTML = '';
    
    // Show options if available
    if (question.options) {
        const optionsGroup = document.getElementById('optionsGroup');
        question.options.forEach(option => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.textContent = option;
            btn.addEventListener('click', () => {
                document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                document.getElementById('textInput').value = option;
                updateNextButton();
            });
            optionsGroup.appendChild(btn);
        });
    } else {
        // Show text input
        document.getElementById('textInput').placeholder = question.placeholder || 'Type your answer...';
        
        // Show suggested options
        if (suggestedAnswers[question.id]) {
            const suggestedGroup = document.getElementById('suggestedOptions');
            suggestedAnswers[question.id].forEach(suggestion => {
                const chip = document.createElement('button');
                chip.className = 'suggestion-chip';
                chip.textContent = suggestion;
                chip.addEventListener('click', () => {
                    const currentValue = document.getElementById('textInput').value;
                    if (question.id === 'countries' || question.id === 'field') {
                        // Allow multiple selections
                        const values = currentValue ? currentValue.split(',').map(v => v.trim()) : [];
                        if (!values.includes(suggestion)) {
                            values.push(suggestion);
                            document.getElementById('textInput').value = values.join(', ');
                        }
                    } else {
                        document.getElementById('textInput').value = suggestion;
                    }
                    updateNextButton();
                });
                suggestedGroup.appendChild(chip);
            });
        }
    }
    
    // Show skip button if not required
    document.getElementById('skipBtn').style.display = question.required ? 'none' : 'inline-flex';
    
    // Speak question
    speak(question.text);
    
    // Update next button
    updateNextButton();
}

function updateNextButton() {
    const input = document.getElementById('textInput').value.trim();
    const selectedOption = document.querySelector('.option-btn.selected');
    const hasAnswer = input || selectedOption;
    const nextBtn = document.getElementById('nextBtn');
    
    nextBtn.disabled = !hasAnswer;
    
    if (currentQuestionIndex === questions.length - 1) {
        nextBtn.querySelector('span').textContent = 'Find Matches';
    } else {
        nextBtn.querySelector('span').textContent = 'Next Question';
    }
}

function handleNextQuestion() {
    const input = document.getElementById('textInput').value.trim();
    if (!input) return;
    
    const question = questions[currentQuestionIndex];
    answers[question.id] = input;
    
    stopListening();
    
    if (currentQuestionIndex < questions.length - 1) {
        loadQuestion(currentQuestionIndex + 1);
    } else {
        processAnswers();
    }
}

function handleSkip() {
    if (currentQuestionIndex < questions.length - 1) {
        loadQuestion(currentQuestionIndex + 1);
    } else {
        processAnswers();
    }
}

function processAnswers() {
    showScreen('processingScreen');
    updateStatus('processing');
    
    // Animate processing steps
    const steps = document.querySelectorAll('.step');
    steps.forEach((step, index) => {
        setTimeout(() => {
            steps.forEach(s => s.classList.remove('active'));
            step.classList.add('active');
        }, index * 1000);
    });
    
    // Save onboarding answers first
    saveOnboardingAnswers()
    .then(() => {
        // After saving, show results (will fetch from API)
        setTimeout(() => {
            showResults();
        }, 3000);
    })
    .catch(error => {
        console.error('Error saving onboarding:', error);
        // Still show results page even if save fails
        setTimeout(() => {
            showResults();
        }, 3000);
    });
}

function saveOnboardingAnswers() {
    // Convert answers to the format expected by the backend
    const formattedAnswers = {
        q1: answers.countries || '',
        q2: answers.qualification || '',
        q3: answers.field || '',
        q4: answers.gaps ? parseInt(answers.gaps) || 0 : 0,
        q5_min: answers.budget ? parseFloat(answers.budget.split('-')[0]?.replace(/[^0-9.]/g, '')) || 0 : 0,
        q5_max: answers.budget ? parseFloat(answers.budget.split('-')[1]?.replace(/[^0-9.]/g, '')) || 100000 : 100000,
        q6: answers.study_preference || '',
        q7: answers.qualification || '',
        q8: answers.english || '',
        q9: answers.study_preference || '',
        q10: answers.career_goals || '',
        q11: answers.scholarship === 'Yes' ? 'Essential' : answers.scholarship === 'Maybe' ? 'Important' : 'Not Required',
        q12: answers.timeline || ''
    };
    
    return fetch('/api/onboarding/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formattedAnswers)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Onboarding saved successfully');
            return data;
        } else {
            throw new Error(data.error || 'Failed to save onboarding');
        }
    });
}

function generateMockMatches() {
    // No longer generating mock matches
    // Actual matches will be fetched from API
    return [];
}

async function showResults(matches) {
    showScreen('resultsScreen');
    
    const resultsContent = document.getElementById('resultsContent');
    resultsContent.innerHTML = '<div class="loading-text">Loading your matches...</div>';
    
    try {
        // Fetch actual matches from the API
        const response = await fetch('/api/matches?page=1&per_page=10');
        const data = await response.json();
        
        const actualMatches = data.matches || [];
        document.getElementById('matchCount').textContent = data.total || 0;
        
        resultsContent.innerHTML = '';
        
        if (actualMatches.length === 0) {
            resultsContent.innerHTML = '<div class="no-matches">No matches found. Please try adjusting your preferences.</div>';
            return;
        }
        
        actualMatches.forEach((match, index) => {
            setTimeout(() => {
                const card = document.createElement('div');
                card.className = 'match-card';
                card.style.animationDelay = `${index * 0.1}s`;
                card.innerHTML = `
                    <div class="match-score">${Math.round(match.match_score)}% Match</div>
                    <h3>${match.name || 'University'}</h3>
                    <div class="country">${match.country || 'N/A'}</div>
                    <div class="match-details">
                        <div><strong>Program:</strong> ${match.course || 'Various Programs'}</div>
                        <div><strong>Estimated Cost:</strong> $${match.total_cost ? match.total_cost.toLocaleString() : 'N/A'}/year</div>
                    </div>
                `;
                resultsContent.appendChild(card);
            }, index * 100);
        });
        
        speak(`Great news! I found ${data.total} university matches for you. Let me show you the top results.`);
    } catch (error) {
        console.error('Error fetching matches:', error);
        resultsContent.innerHTML = '<div class="error-text">Error loading matches. Please go to dashboard to view your results.</div>';
        document.getElementById('matchCount').textContent = '0';
    }
}

function resetOnboarding() {
    currentQuestionIndex = 0;
    answers = {};
    stopListening();
    showScreen('onboardingScreen');
    loadQuestion(0);
}

