// Projects Gallery - Interactive Effects and Lightbox

// Typewriter effect for title
const titleText = "AI-Powered Projects";
const titleElement = document.getElementById('gallery-title');
let titleIndex = 0;

function typeTitle() {
    if (titleIndex < titleText.length) {
        const char = titleText.charAt(titleIndex);
        titleElement.textContent += char;
        titleIndex++;
        setTimeout(typeTitle, 80);
    } else {
        // Add blinking cursor after typing
        const cursor = document.createElement('span');
        cursor.className = 'title-cursor';
        cursor.textContent = '|';
        titleElement.appendChild(cursor);
    }
}

// Start typing after page load
setTimeout(typeTitle, 300);

// Performance optimization: Load GIFs on hover
const projectContainers = document.querySelectorAll('.project-image-container');
projectContainers.forEach(container => {
    const img = container.querySelector('.project-image-static');
    const gifUrl = container.dataset.gif;
    const staticUrl = container.dataset.static;
    let gifLoaded = false;

    container.addEventListener('mouseenter', () => {
        if (gifUrl && !gifLoaded) {
            // Preload the GIF
            const gifImg = new Image();
            gifImg.src = gifUrl;
            gifImg.onload = () => {
                img.src = gifUrl;
                gifLoaded = true;
            };
        } else if (gifLoaded) {
            img.src = gifUrl;
        }
    });

    container.addEventListener('mouseleave', () => {
        if (gifLoaded && staticUrl) {
            img.src = staticUrl;
        }
    });
});

// Cursor follower glow effect
const cursorGlow = document.querySelector('.cursor-glow');
let mouseX = 0;
let mouseY = 0;
let glowX = 0;
let glowY = 0;

document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
});

function animateGlow() {
    // Smooth follow with easing
    glowX += (mouseX - glowX) * 0.15;
    glowY += (mouseY - glowY) * 0.15;

    cursorGlow.style.left = glowX + 'px';
    cursorGlow.style.top = glowY + 'px';

    requestAnimationFrame(animateGlow);
}

animateGlow();

// Interactive hover effects for title
const galleryTitle = document.getElementById('gallery-title');

galleryTitle.addEventListener('mouseenter', () => {
    galleryTitle.style.transform = 'scale(1.05)';
});

galleryTitle.addEventListener('mouseleave', () => {
    galleryTitle.style.transform = 'scale(1)';
});

// Lightbox functionality
function openLightbox(projectName) {
    const lightbox = document.getElementById('lightbox');
    const lightboxGallery = document.getElementById('lightbox-gallery');
    const lightboxTitle = document.getElementById('lightbox-project-title');
    const lightboxTopCta = document.getElementById('lightbox-top-cta');

    // Project data mapping - only showing GIFs for performance
    const projectData = {
        'moodflix': {
            title: 'MoodFlix',
            image: '/media/Moodflix2.gif',
            link: null
        },
        'planno': {
            title: 'Planno',
            image: '/media/Planno.gif',
            link: 'https://planno-eta.vercel.app/'
        },
        'leairn': {
            title: 'LeAIrn',
            image: '/media/Meeting.gif',
            link: '/'
        },
        'portfolio': {
            title: 'Chris Buzaid Portfolio',
            image: '/media/Portfolio.gif',
            link: 'https://chrisbuzaid.dev'
        }
    };

    const project = projectData[projectName];

    // Set title
    lightboxTitle.textContent = project.title;

    // Clear previous images
    lightboxGallery.textContent = '';

    // Add only the main GIF for better performance
    const imgElement = document.createElement('img');
    imgElement.src = project.image;
    imgElement.alt = `${project.title} preview`;
    imgElement.className = 'lightbox-gallery-image';
    lightboxGallery.appendChild(imgElement);

    // Show/hide and set link for top CTA button only
    if (project.link && project.link !== '#') {
        lightboxTopCta.href = project.link;
        lightboxTopCta.style.display = 'inline-flex';
    } else {
        lightboxTopCta.style.display = 'none';
    }

    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
}

// Close lightbox with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeLightbox();
        closeComingSoon();
    }
});

// Coming Soon Modal Functions
function showComingSoon(event) {
    if (event) event.preventDefault();
    const modal = document.getElementById('coming-soon-modal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeComingSoon() {
    const modal = document.getElementById('coming-soon-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}
