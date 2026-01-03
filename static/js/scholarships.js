// Scholarship Finder JavaScript

const scholarships = [
    {
        id: '1',
        name: 'International Excellence Scholarship',
        provider: 'University of Cambridge',
        amount: 25000,
        type: 'merit',
        country: 'UK',
        eligibility: ['GPA > 3.5', 'IELTS > 7.0', 'International Student'],
        deadline: '2025-03-15',
        successRate: 75,
        matchScore: 92,
        requirements: ['Academic transcripts', 'Personal statement', 'Letter of recommendation']
    },
    {
        id: '2',
        name: 'Global Leaders Scholarship',
        provider: 'University of Toronto',
        amount: 15000,
        type: 'partial',
        country: 'Canada',
        eligibility: ['GPA > 3.0', 'Leadership experience', 'Community service'],
        deadline: '2025-04-01',
        successRate: 65,
        matchScore: 88,
        requirements: ['Resume', 'Essay', 'Reference letters']
    },
    {
        id: '3',
        name: 'DAAD Scholarship',
        provider: 'German Academic Exchange',
        amount: 30000,
        type: 'full',
        country: 'Germany',
        eligibility: ['Master\'s program', 'Research proposal', 'German language (B1)'],
        deadline: '2025-02-28',
        successRate: 45,
        matchScore: 78,
        requirements: ['Research proposal', 'CV', 'Language certificate', 'Motivation letter']
    },
    {
        id: '4',
        name: 'Chevening Scholarship',
        provider: 'UK Government',
        amount: 50000,
        type: 'full',
        country: 'UK',
        eligibility: ['Work experience 2+ years', 'Leadership potential', 'UK university offer'],
        deadline: '2025-11-02',
        successRate: 35,
        matchScore: 72,
        requirements: ['Work experience proof', 'Leadership essay', 'Two references', 'University offer']
    },
    {
        id: '5',
        name: 'Australia Awards Scholarship',
        provider: 'Australian Government',
        amount: 40000,
        type: 'full',
        country: 'Australia',
        eligibility: ['Undergraduate/Master\'s', 'Academic excellence', 'English proficiency'],
        deadline: '2025-04-30',
        successRate: 40,
        matchScore: 85,
        requirements: ['Academic transcripts', 'English test scores', 'Personal statement']
    }
];

function getTypeColor(type) {
    const colors = {
        'full': '#10b981',
        'partial': '#3b82f6',
        'merit': '#8b5cf6',
        'need-based': '#f59e0b'
    };
    return colors[type] || '#6b7280';
}

function getTypeLabel(type) {
    const labels = {
        'full': 'Full Scholarship',
        'partial': 'Partial',
        'merit': 'Merit-based',
        'need-based': 'Need-based'
    };
    return labels[type] || type;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const daysUntil = Math.floor((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    
    if (daysUntil < 0) return 'Deadline passed';
    if (daysUntil === 0) return 'Due today';
    if (daysUntil === 1) return 'Due tomorrow';
    if (daysUntil <= 30) return `${daysUntil} days remaining`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderScholarships() {
    const searchTerm = document.getElementById('scholarshipSearch').value.toLowerCase();
    const filterCountry = document.getElementById('scholarshipCountry').value;
    const filterType = document.getElementById('scholarshipType').value;
    
    const filtered = scholarships.filter(scholarship => {
        const matchesSearch = scholarship.name.toLowerCase().includes(searchTerm) ||
                            scholarship.provider.toLowerCase().includes(searchTerm);
        const matchesCountry = filterCountry === 'all' || scholarship.country === filterCountry;
        const matchesType = filterType === 'all' || scholarship.type === filterType;
        
        return matchesSearch && matchesCountry && matchesType;
    }).sort((a, b) => b.matchScore - a.matchScore);
    
    const container = document.getElementById('scholarshipList');
    container.innerHTML = '';
    
    if (filtered.length === 0) {
        container.innerHTML = '<p class="no-results">No scholarships found matching your criteria.</p>';
        return;
    }
    
    filtered.forEach(scholarship => {
        const card = document.createElement('div');
        card.className = 'scholarship-card';
        card.innerHTML = `
            <div class="scholarship-header">
                <div>
                    <h3>${scholarship.name}</h3>
                    <p class="scholarship-provider">${scholarship.provider}</p>
                </div>
                <div class="scholarship-badges">
                    <span class="scholarship-type" style="background: ${getTypeColor(scholarship.type)}">
                        ${getTypeLabel(scholarship.type)}
                    </span>
                    <span class="scholarship-match">${scholarship.matchScore}% Match</span>
                </div>
            </div>
            <div class="scholarship-details">
                <div class="detail-item">
                    <i class="fas fa-dollar-sign"></i>
                    <span>$${scholarship.amount.toLocaleString()}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-globe"></i>
                    <span>${scholarship.country}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-calendar"></i>
                    <span>${formatDate(scholarship.deadline)}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-chart-line"></i>
                    <span>${scholarship.successRate}% Success Rate</span>
                </div>
            </div>
            <div class="scholarship-eligibility">
                <strong>Eligibility:</strong>
                <ul>
                    ${scholarship.eligibility.map(e => `<li>${e}</li>`).join('')}
                </ul>
            </div>
            <div class="scholarship-requirements">
                <strong>Requirements:</strong>
                <ul>
                    ${scholarship.requirements.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
            <div class="scholarship-actions">
                <button class="btn btn-primary">Apply Now</button>
                <button class="btn btn-secondary">Save for Later</button>
            </div>
        `;
        container.appendChild(card);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    renderScholarships();
    
    document.getElementById('scholarshipSearch').addEventListener('input', renderScholarships);
    document.getElementById('scholarshipCountry').addEventListener('change', renderScholarships);
    document.getElementById('scholarshipType').addEventListener('change', renderScholarships);
});

