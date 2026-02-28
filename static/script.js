// Localization Dictionary
let translations = {
    // Initial minimal fallback to prevent immediate errors
    "tr": { "page_title_home": "Araçlar & Dönüştürücü", "supported_formats": "Desteklenen Formatlar" },
    "en": { "page_title_home": "Tools & Converter", "supported_formats": "Supported Formats" },
    "de": { "page_title_home": "Werkzeuge & Konverter", "supported_formats": "Unterstützte Formate" }
};
let translationsLoaded = false;

let currentLang = localStorage.getItem('lang') || 'tr';

async function initTranslations() {
    try {
        const res = await fetch('translations.json');
        if (res.ok) {
            translations = await res.json();
            translationsLoaded = true;
            applyLanguage();
        } else {
            console.warn("Translations fetch failed with status:", res.status);
        }
    } catch (e) {
        console.warn("Translations fetch network error:", e);
    }
}

function applyLanguage() {
    if (!translationsLoaded) return;
    const t = translations[currentLang];
    if (!t) return;

    // Apply standard text or standard placeholder translations
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            const attr = el.getAttribute('data-i18n-attr');
            if (attr) {
                el.setAttribute(attr, t[key]);
            } else if (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'password')) {
                el.placeholder = t[key];
            } else {
                el.textContent = t[key];
            }
        }
    });

    // Apply title attributes specifically
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (t[key]) {
            el.setAttribute('title', t[key]);
        }
    });

    const dp = document.getElementById('drop-file-types');
    if (dp && currentTool) {
        dp.textContent = `${t.supported_formats}: ${toolConfig[currentTool].validExtensions.join(', ')}`;
    }

    // Refresh Tool Content if changed
    if (currentTool) switchTool(currentTool);
}

// Theme Initialization
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            themeToggle.textContent = next === 'dark' ? '☀️' : '🌙';
        });
    }

    // Language logic setup (Custom Dropdown)
    const langBtn = document.getElementById('lang-btn');
    const langMenu = document.getElementById('lang-menu');
    const langText = document.getElementById('current-lang-text');

    if (langBtn && langMenu) {
        // Init state
        langText.textContent = currentLang.toUpperCase();
        langMenu.querySelectorAll('li').forEach(li => {
            if (li.dataset.lang === currentLang) li.classList.add('active');
        });

        langBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            langMenu.classList.toggle('show');
        });

        document.addEventListener('click', () => {
            langMenu.classList.remove('show');
        });

        langMenu.querySelectorAll('li').forEach(item => {
            item.addEventListener('click', (e) => {
                currentLang = e.currentTarget.dataset.lang;
                localStorage.setItem('lang', currentLang);

                langText.textContent = currentLang.toUpperCase();
                langMenu.querySelectorAll('li').forEach(li => li.classList.remove('active'));
                e.currentTarget.classList.add('active');

                applyLanguage();
            });
        });
    }

    initTranslations();
});

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const fileNameDisplay = document.getElementById('file-name');
const progressText = document.getElementById('progress-text');
const resultContainer = document.getElementById('result-container');
const downloadBtn = document.getElementById('download-btn');
const resetBtn = document.getElementById('reset-btn');
const toastContainer = document.getElementById('toast-container');
const countdownTimer = document.getElementById('countdown-timer');

// New elements for tool switching
const toolsDashboard = document.getElementById('tools-dashboard');
const dropZoneContainer = document.getElementById('drop-zone-container');
const backToHomeBtn = document.getElementById('back-to-home');
const toolCards = document.querySelectorAll('.tool-card');
const navLinks = document.querySelectorAll('.nav-link');
const toolActiveTitle = document.getElementById('tool-active-title');
const dropFileTypes = document.getElementById('drop-file-types');
const pageTitle = document.getElementById('page-title');
const pageDesc = document.getElementById('page-desc');

const watermarkInputPanel = document.getElementById('watermark-input-panel');
const watermarkTextInput = document.getElementById('watermark-text');
const startWatermarkBtn = document.getElementById('start-watermark-btn');

const passwordInputPanel = document.getElementById('password-input-panel');
const passwordInput = document.getElementById('password-input');
const startPasswordBtn = document.getElementById('start-password-btn');
const passwordPanelTitle = document.getElementById('password-panel-title');

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
let currentTool = 'convert';
let countdownInterval = null;

const toolConfig = {
    'convert': {
        titleKey: 'tool_convert_title',
        descKey: 'tool_convert_desc',
        endpoint: '/upload/',
        multiple: true,
        validExtensions: ['.pptx', '.pdf', '.docx', '.png', '.jpg', '.jpeg'],
        pageTitleKey: 'page_title_home',
        pageDescKey: 'page_desc_home'
    },
    'merge': {
        titleKey: 'tool_merge_title',
        endpoint: '/merge/',
        multiple: true,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_merge_title',
        pageDescKey: 'tool_merge_desc'
    },
    'split': {
        titleKey: 'tool_split_title',
        endpoint: '/split/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_split_title',
        pageDescKey: 'tool_split_desc'
    },
    'compress': {
        titleKey: 'tool_compress_title',
        endpoint: '/compress/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_compress_title',
        pageDescKey: 'tool_compress_desc'
    },
    'rotate': {
        titleKey: 'tool_rotate_title',
        endpoint: '/rotate/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_rotate_title',
        pageDescKey: 'tool_rotate_desc'
    },
    'watermark': {
        titleKey: 'tool_watermark_title',
        endpoint: '/watermark/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_watermark_title',
        pageDescKey: 'tool_watermark_desc'
    },
    'pdf-to-image': {
        titleKey: 'tool_pdf2img_title',
        endpoint: '/pdf-to-image/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_pdf2img_title',
        pageDescKey: 'tool_pdf2img_desc'
    },
    'protect': {
        titleKey: 'tool_protect_title',
        endpoint: '/protect/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_protect_title',
        pageDescKey: 'tool_protect_desc'
    },
    'unlock': {
        titleKey: 'tool_unlock_title',
        endpoint: '/unlock/',
        multiple: false,
        validExtensions: ['.pdf'],
        pageTitleKey: 'tool_unlock_title',
        pageDescKey: 'tool_unlock_desc'
    }
};

// Switch tool
function switchTool(toolId) {
    currentTool = toolId;
    const config = toolConfig[toolId];

    if (!translationsLoaded) return;
    const t = translations[currentLang];

    // Update UI headers dynamically
    pageTitle.textContent = t[config.pageTitleKey] || t[config.titleKey];
    pageDesc.textContent = t[config.pageDescKey] || t[config.descKey] || '';
    toolActiveTitle.textContent = t[config.titleKey];
    dropFileTypes.textContent = `${t.supported_formats}: ${config.validExtensions.join(', ')}`;

    // Control file input attributes
    if (config.multiple) {
        fileInput.setAttribute('multiple', 'multiple');
    } else {
        fileInput.removeAttribute('multiple');
    }

    // Update active nav link
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.dataset.target === toolId || (toolId === 'convert' && link.dataset.target === 'home')) {
            link.classList.add('active');
        }
    });

    // Hide dashboard, show dropzone
    toolsDashboard.classList.add('hidden');
    const recentPanel = document.getElementById('recent-tasks-panel');
    if (recentPanel) recentPanel.classList.add('hidden');
    dropZoneContainer.classList.remove('hidden');
    resetUI(); // Clear any previous states

    // Explicitly handle compress level panel
    const compressLevelPanel = document.getElementById('compress-level-selection');
    if (toolId === 'compress') {
        compressLevelPanel.classList.remove('hidden');
    } else {
        compressLevelPanel.classList.add('hidden');
    }
}

function showHome() {
    const t = translations[currentLang];
    pageTitle.textContent = t.page_title_home;
    pageDesc.textContent = t.page_desc_home;

    toolsDashboard.classList.remove('hidden');
    dropZoneContainer.classList.add('hidden');
    progressContainer.classList.add('hidden');
    resultContainer.classList.add('hidden');
    renderRecentTasks();

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.dataset.target === 'home') link.classList.add('active');
    });
}

// Event Listeners for Tool Selection
toolCards.forEach(card => {
    card.addEventListener('click', () => {
        switchTool(card.dataset.tool);
    });
});

navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = link.dataset.target;
        if (target === 'home') {
            showHome();
        } else {
            switchTool(target);
        }
    });
});

backToHomeBtn.addEventListener('click', showHome);

// Recent Tasks Logic
function renderRecentTasks() {
    const list = document.getElementById('recent-tasks-list');
    const panel = document.getElementById('recent-tasks-panel');
    if (!list || !panel) return;
    let tasks = JSON.parse(localStorage.getItem('recentTasks') || '[]');
    if (tasks.length === 0) {
        panel.classList.add('hidden');
        return;
    }
    panel.classList.remove('hidden');
    list.innerHTML = '';
    tasks.forEach(t => {
        const d = new Date(t.time);
        const li = document.createElement('li');
        li.innerHTML = `<span class="task-time">${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}</span> 
                        <span class="task-type">${t.taskName}</span> 
                        <span class="task-file" title="${t.fileName}">${t.fileName}</span>
                        ${t.success ? '<span class="status-ok">✓</span>' : '<span class="status-err">✗</span>'}`;
        list.appendChild(li);
    });
}

function addRecentTask(taskName, fileName, success = true) {
    let tasks = JSON.parse(localStorage.getItem('recentTasks') || '[]');
    tasks.unshift({ taskName, fileName, time: new Date().toISOString(), success });
    if (tasks.length > 5) tasks.pop();
    localStorage.setItem('recentTasks', JSON.stringify(tasks));
    renderRecentTasks();
}
document.addEventListener('DOMContentLoaded', renderRecentTasks);

// Drag & Drop Events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
});

dropZone.addEventListener('drop', handleDrop, false);
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFiles(e.target.files);
});

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length) handleFiles(files);
}

const targetFormatPanel = document.getElementById('target-format-selection');
const formatOptionsGrid = document.getElementById('format-options');
const startConvertBtn = document.getElementById('start-convert-btn');

const compressLevelPanel = document.getElementById('compress-level-selection');
const compressOptionsDiv = document.querySelectorAll('#compress-options .format-option-card');

let selectedTargetFormat = null;
let currentFilesPending = [];
let selectedCompressLevel = 'medium';

const formatDefinitions = {
    'pdf': { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>', label: 'PDF' },
    'docx': { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><text x="9" y="16" font-size="8" font-family="Arial" font-weight="bold">W</text></svg>', label: 'Word' },
    'pptx': { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><text x="10" y="16" font-size="8" font-family="Arial" font-weight="bold">P</text></svg>', label: 'PowerPoint' },
    'jpg': { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>', label: 'JPG' },
    'xlsx': { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><text x="10" y="16" font-size="8" font-family="Arial" font-weight="bold">X</text></svg>', label: 'Excel' }
};

function showTargetFormatSelection(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    let options = [];

    if (ext === 'pdf') {
        options = ['docx', 'pptx', 'jpg', 'xlsx'];
    } else if (['docx', 'pptx', 'jpg', 'jpeg', 'png'].includes(ext)) {
        options = ['pdf'];
    }

    formatOptionsGrid.innerHTML = '';
    selectedTargetFormat = null;
    startConvertBtn.disabled = true;

    options.forEach(fmt => {
        const def = formatDefinitions[fmt];
        const card = document.createElement('div');
        card.className = 'format-option-card';
        card.dataset.format = fmt;
        card.innerHTML = `
            ${def.icon}
            <span>${translationsLoaded && translations[currentLang][`format_${fmt}`] ? translations[currentLang][`format_${fmt}`] : def.label}</span>
            <div class="checkmark">✓</div>
        `;

        card.addEventListener('click', () => {

            document.querySelectorAll('.format-option-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedTargetFormat = fmt;
            startConvertBtn.disabled = false;
        });

        formatOptionsGrid.appendChild(card);
    });

    document.getElementById('drop-zone').classList.add('hidden');
    targetFormatPanel.classList.remove('hidden');
}

// Compress logic
compressOptionsDiv.forEach(opt => {
    opt.addEventListener('click', () => {
        compressOptionsDiv.forEach(c => c.classList.remove('selected'));
        opt.classList.add('selected');
        selectedCompressLevel = opt.dataset.level;
    });
});

startConvertBtn.addEventListener('click', () => {
    if (currentFilesPending.length > 0 && selectedTargetFormat) {
        uploadAndConvert(currentFilesPending);
    }
});

startWatermarkBtn.addEventListener('click', () => {
    if (currentFilesPending.length > 0) {
        const text = watermarkTextInput.value.trim();
        if (!text) {
            showToast(translations[currentLang].err_empty, 'error');
            return;
        }
        uploadAndConvert(currentFilesPending);
    }
});

startPasswordBtn.addEventListener('click', () => {
    if (currentFilesPending.length > 0) {
        const pass = passwordInput.value;
        if (!pass) {
            showToast(translations[currentLang].err_empty, 'error');
            return;
        }
        uploadAndConvert(currentFilesPending);
    }
});

async function generateThumbnails(files) {
    const previewPanel = document.getElementById('preview-panel');
    const thumbnailsContainer = document.getElementById('preview-thumbnails');

    // Clear old thumbnails but keep container visible if files exist
    thumbnailsContainer.innerHTML = '';

    let hasPdf = false;
    for (const file of files) {
        if (file.name.toLowerCase().endsWith('.pdf')) {
            hasPdf = true;

            // Create placeholder
            const thumbDiv = document.createElement('div');
            thumbDiv.className = 'thumbnail-item';
            thumbDiv.innerHTML = `
                <div class="loader-container">
                    <div class="spinner"></div>
                </div>
                <span>${file.name}</span>
            `;
            thumbnailsContainer.appendChild(thumbDiv);

            // Fetch preview
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/preview/', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.thumbnail) {
                        thumbDiv.innerHTML = `
                            <img src="${data.thumbnail}" alt="Preview">
                            <span>${file.name}</span>
                        `;
                    } else {
                        const t = translationsLoaded ? translations[currentLang] : translations['tr'];
                        const kilitliText = t.kilitli_hata || 'Kilitli/Hata';
                        thumbDiv.innerHTML = `
                            <div style="width:100px; height:140px; background:#30363d; border-radius:4px; margin-bottom:8px; display:flex; align-items:center; justify-content:center;">
                                <span style="color:#8b949e; font-size:0.8rem; text-align:center;">${kilitliText}</span>
                            </div>
                            <span>${file.name}</span>
                        `;
                    }
                }
            } catch (e) {
                console.error("Preview fetch err", e);
            }
        }
    }

    if (hasPdf) {
        previewPanel.classList.remove('hidden');
    } else {
        previewPanel.classList.add('hidden');
    }
}

function handleFiles(files) {
    const config = toolConfig[currentTool];
    const fileArray = Array.from(files);
    const t = translations[currentLang];

    if (!config.multiple && fileArray.length > 1) {
        showToast(t.err_multi, 'error');
        return;
    }

    if (currentTool === 'merge' && fileArray.length < 2) {
        showToast(t.err_merge, 'error');
        return;
    }

    // Validate Files
    for (let file of fileArray) {
        const sizeLimit = currentTool === 'compress' ? MAX_FILE_SIZE * 5 : MAX_FILE_SIZE;
        if (file.size > sizeLimit) {
            showToast(t.err_size, 'error');
            return;
        }

        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!config.validExtensions.includes(ext)) {
            showToast(t.err_format, 'error');
            return;
        }
    }

    if (currentTool === 'convert') {
        currentFilesPending = fileArray;
        showTargetFormatSelection(currentFilesPending[0]);
    } else if (currentTool === 'compress') {
        // Compress levels are already visible, just upload directly
        uploadAndConvert([fileArray[0]]);
    } else if (currentTool === 'watermark') {
        currentFilesPending = [fileArray[0]];
        document.getElementById('drop-zone').classList.add('hidden');
        watermarkInputPanel.classList.remove('hidden');
    } else if (currentTool === 'protect') {
        currentFilesPending = [fileArray[0]];
        document.getElementById('drop-zone').classList.add('hidden');
        passwordPanelTitle.textContent = t.pwd_encrypt_title || "PDF'i Korumak İçin Şifre Belirleyin";
        passwordInput.value = '';
        passwordInputPanel.classList.remove('hidden');
    } else if (currentTool === 'unlock') {
        currentFilesPending = [fileArray[0]];
        document.getElementById('drop-zone').classList.add('hidden');
        passwordPanelTitle.textContent = t.pwd_decrypt_title || "PDF Şifresini Girin";
        passwordInput.value = '';
        passwordInputPanel.classList.remove('hidden');
    } else {
        uploadAndConvert(fileArray);
    }

    // Generate previews
    generateThumbnails(fileArray);
}

function startCountdown() {
    if (countdownInterval) clearInterval(countdownInterval);
    let timeLeft = 600; // 10 minutes

    const updateTimer = () => {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        countdownTimer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        if (timeLeft <= 0) {
            clearInterval(countdownInterval);
            countdownTimer.textContent = '00:00';
            showToast(translations[currentLang].toast_deleted, 'success');
        } else {
            timeLeft--;
        }
    };

    updateTimer();
    countdownInterval = setInterval(updateTimer, 1000);
}

async function uploadAndConvert(files) {
    const config = toolConfig[currentTool];

    // UI Updates
    dropZoneContainer.classList.add('hidden');
    resultContainer.classList.add('hidden');
    progressContainer.classList.remove('hidden');

    const t = translations[currentLang];

    if (files.length > 1) {
        fileNameDisplay.textContent = `${files.length} ${t.files_selected || 'dosya seçildi'}`;
    } else {
        fileNameDisplay.textContent = files[0].name;
    }

    progressBar.style.width = "0%";

    const formData = new FormData();

    if (currentTool === 'merge' || currentTool === 'convert') {
        files.forEach(file => formData.append('files', file));
        if (currentTool === 'merge') {
            progressText.textContent = t.converting;
        } else {
            formData.append('target_format', selectedTargetFormat);
            progressText.textContent = t.converting;
        }
    } else {
        formData.append('file', files[0]);
        if (currentTool === 'rotate') {
            formData.append('degrees', 90);
            progressText.textContent = t.converting;
        } else if (currentTool === 'compress') {
            formData.append('level', selectedCompressLevel);
            progressText.textContent = t.converting;
        } else if (currentTool === 'watermark') {
            formData.append('text', watermarkTextInput.value.trim());
            progressText.textContent = t.converting;
        } else if (currentTool === 'protect' || currentTool === 'unlock') {
            formData.append('password', passwordInput.value);
            progressText.textContent = t.converting;
        } else {
            progressText.textContent = t.converting;
        }
    }

    try {
        progressContainer.classList.add('converting');

        const xhr = new XMLHttpRequest();

        const response = await new Promise((resolve, reject) => {
            let endpoint = config.endpoint;
            if (currentTool === 'convert' && selectedTargetFormat === 'jpg') {
                endpoint = '/convert/jpg/';
            } else if (currentTool === 'convert' && selectedTargetFormat === 'xlsx') {
                endpoint = '/convert/excel/';
            }
            xhr.open('POST', endpoint, true);

            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    let err = t.err_unknown || "Bilinmeyen Hata";
                    try { err = JSON.parse(xhr.responseText).detail || xhr.statusText; } catch { }
                    reject(new Error(err));
                }
            };

            xhr.onerror = () => reject(new Error(t.err_network || 'Ağ hatası oluştu. Sunucuya bağlanılamadı.'));
            xhr.send(formData);
        });

        // Conversion done
        progressContainer.classList.remove('converting');
        progressBar.style.width = '100%';
        progressText.textContent = "OK";

        setTimeout(() => {
            showResult(response.download_url);
            startCountdown();
        }, 500);

        showToast(response.message || t.toast_success, 'success');
        addRecentTask(t[toolConfig[currentTool].titleKey], files.length > 1 ? `${files.length} ${t.files_processed || 'dosya işlendi'}` : files[0].name, true);

    } catch (error) {
        showToast(error.message, 'error');
        addRecentTask(t[toolConfig[currentTool].titleKey], files.length > 1 ? `${files.length} ${t.files_processed || 'dosya işlendi'}` : files[0].name, false);
        resetUI();
    }
}

function showResult(url) {
    progressContainer.classList.add('hidden');
    resultContainer.classList.remove('hidden');
    downloadBtn.href = url;
}

function resetUI() {
    dropZoneContainer.classList.remove('hidden');
    document.getElementById('drop-zone').classList.remove('hidden');
    targetFormatPanel.classList.add('hidden');
    // Keep compress levels visible if we are currently on the compress tool
    if (currentTool !== 'compress') {
        compressLevelPanel.classList.add('hidden');
    }
    watermarkInputPanel.classList.add('hidden');
    passwordInputPanel.classList.add('hidden');
    progressContainer.classList.add('hidden');
    resultContainer.classList.add('hidden');
    progressContainer.classList.remove('converting');
    progressBar.style.width = '0%';
    fileInput.value = '';
    selectedTargetFormat = null;
    currentFilesPending = [];
    startConvertBtn.disabled = true;
    if (countdownInterval) clearInterval(countdownInterval);
}

resetBtn.addEventListener('click', resetUI);

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-closing');
        toast.addEventListener('animationend', () => {
            toast.remove();
        });
    }, 4000);
}
