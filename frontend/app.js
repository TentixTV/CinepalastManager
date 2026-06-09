// --- State Management ---
let appState = {
    movies: [],
    popularMovies: [],
    onlineSearchResults: [],
    viewMode: 'Galerie', // 'Galerie' or 'Tabelle'
    config: {},
    currentMovie: null,
    searchQuery: '',
    searchFilter: 'Alles',
    isSearchingOnline: false
};

// --- DOM References ---
const dom = {
    searchFilter: document.getElementById('search-filter'),
    searchInput: document.getElementById('search-input'),
    clearSearch: document.getElementById('clear-search'),
    viewGallery: document.getElementById('view-gallery'),
    viewTable: document.getElementById('view-table'),
    movieGrid: document.getElementById('movie-grid'),
    movieTableWrapper: document.getElementById('movie-table-wrapper'),
    movieTableBody: document.getElementById('movie-table-body'),
    emptyState: document.getElementById('empty-state'),
    btnEmptyOnlineSearch: document.getElementById('btn-empty-online-search'),
    btnAddMovie: document.getElementById('btn-add-movie'),
    btnSettings: document.getElementById('btn-settings'),
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingText: document.getElementById('loading-text')
};

// --- Custom Dialog Modal Helpers ---
function showCustomAlert(message, title = "Hinweis") {
    document.getElementById('alert-title').innerText = title;
    document.getElementById('alert-message').innerText = message;
    openModal('modal-alert');
}

function showCustomConfirm(message, title = "Bestätigung") {
    return new Promise((resolve) => {
        document.getElementById('confirm-title').innerText = title;
        document.getElementById('confirm-message').innerText = message;
        
        const okBtn = document.getElementById('btn-confirm-ok');
        const cancelBtn = document.getElementById('btn-confirm-cancel');
        
        const onOk = () => {
            closeModal('modal-confirm');
            cleanup();
            resolve(true);
        };
        
        const onCancel = () => {
            closeModal('modal-confirm');
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
        };
        
        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        
        openModal('modal-confirm');
    });
}

// --- Initialization ---
window.addEventListener('DOMContentLoaded', () => {
    showLoading("Initialisiere CinePalast...");
    
    // Check if pywebview is loaded. If yes, init immediately, otherwise wait for its event.
    if (window.pywebview) {
        initApp();
    } else {
        window.addEventListener('pywebviewready', initApp);
    }
});

async function initApp() {
    try {
        // 1. Load config
        appState.config = await pywebview.api.load_config();
        
        // 2. Set theme
        applyTheme(appState.config.theme || 'cyan');
        
        // 3. Set view mode
        setViewMode(appState.config.default_view || 'Galerie');
        
        // 4. Set search filter dropdown
        dom.searchFilter.value = appState.searchFilter;
        
        // 5. Load popular movies
        try {
            appState.popularMovies = await pywebview.api.get_popular_movies();
        } catch (e) {
            console.error("Failed to load popular movies:", e);
        }
        
        // 6. Load and display movies
        await refreshMovies();
        
        // 7. Bind events
        bindEvents();
        
        hideLoading();
    } catch (e) {
        console.error("Init Error:", e);
        hideLoading();
    }
}

// --- Event Bindings ---
function bindEvents() {
    // Search input typing
    dom.searchInput.addEventListener('input', (e) => {
        appState.searchQuery = e.target.value;
        toggleClearSearchButton();
        performSearch();
    });

    // Support pressing Enter key in search to trigger online search
    dom.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            triggerOnlineSearch();
        }
    });

    // Clear search
    dom.clearSearch.addEventListener('click', () => {
        dom.searchInput.value = '';
        appState.searchQuery = '';
        toggleClearSearchButton();
        performSearch();
    });

    // Filter change
    dom.searchFilter.addEventListener('change', (e) => {
        appState.searchFilter = e.target.value;
        performSearch();
    });

    // View toggles
    dom.viewGallery.addEventListener('click', () => setViewMode('Galerie'));
    dom.viewTable.addEventListener('click', () => setViewMode('Tabelle'));

    // Main buttons
    dom.btnAddMovie.addEventListener('click', () => openMovieForm());
    dom.btnSettings.addEventListener('click', () => openSettings());
    
    // Online search from empty state
    dom.btnEmptyOnlineSearch.addEventListener('click', () => triggerOnlineSearch());
    
    // Settings browse path
    document.getElementById('btn-browse-path').addEventListener('click', browseCustomPath);
    document.getElementById('btn-test-keys').addEventListener('click', testAPIConnections);
    document.getElementById('btn-backup-db').addEventListener('click', backupDatabase);
    document.getElementById('btn-restore-db').addEventListener('click', restoreDatabase);
    document.getElementById('btn-reset-db').addEventListener('click', resetDatabase);
    
    // Movie Form browse assets
    document.getElementById('btn-browse-poster').addEventListener('click', () => browseAsset('poster'));
    document.getElementById('btn-browse-banner').addEventListener('click', () => browseAsset('banner'));
    
    // Details download buttons
    document.getElementById('btn-download-poster').addEventListener('click', () => {
        if (appState.currentMovie) {
            downloadPoster(appState.currentMovie);
        }
    });
    document.getElementById('btn-download-banner').addEventListener('click', () => {
        if (appState.currentMovie) {
            downloadBanner(appState.currentMovie);
        }
    });

    // Show certificate modal link
    const showCertLink = document.getElementById('link-show-cert');
    if (showCertLink) {
        showCertLink.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('modal-certificate');
        });
    }

    // Close modals by clicking outside the container
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                if (overlay.id !== 'modal-alert' && overlay.id !== 'modal-confirm') {
                    closeModal(overlay.id);
                }
            }
        });
    });
}

// --- Loading indicator ---
function showLoading(text = "Lade...") {
    dom.loadingText.innerText = text;
    dom.loadingOverlay.classList.add('active');
}

// --- Hide Loading ---
function hideLoading() {
    dom.loadingOverlay.classList.remove('active');
}

// --- Apply theme colors ---
function applyTheme(themeName) {
    document.body.className = '';
    document.body.classList.add(`theme-${themeName}`);
    document.getElementById('settings-theme').value = themeName;
}

// --- Toggle clear search button ---
function toggleClearSearchButton() {
    if (appState.searchQuery.length > 0) {
        dom.clearSearch.style.display = 'block';
    } else {
        dom.clearSearch.style.display = 'none';
    }
}

// --- Change active view mode ---
function setViewMode(mode) {
    appState.viewMode = mode;
    if (mode === 'Galerie') {
        dom.viewGallery.classList.add('active');
        dom.viewTable.classList.remove('active');
        dom.movieGrid.classList.add('active');
        dom.movieTableWrapper.classList.remove('active');
    } else {
        dom.viewGallery.classList.remove('active');
        dom.viewTable.classList.add('active');
        dom.movieGrid.classList.remove('active');
        dom.movieTableWrapper.classList.add('active');
    }
    renderMovies();
}

// --- Load movies from database ---
async function refreshMovies() {
    if (appState.searchQuery.trim().length > 0) {
        appState.movies = await pywebview.api.search_movies(appState.searchQuery, appState.searchFilter);
    } else {
        appState.movies = await pywebview.api.get_all_movies();
    }
    renderMovies();
}

// --- Perform realtime search ---
let searchDebounceTimeout;
function performSearch() {
    clearTimeout(searchDebounceTimeout);
    const query = appState.searchQuery.trim();
    if (!query) {
        appState.onlineSearchResults = [];
        appState.isSearchingOnline = false;
        refreshMovies();
        return;
    }
    
    // Set loading state immediately and trigger rendering to show loader
    appState.isSearchingOnline = true;
    appState.onlineSearchResults = [];
    
    // Update local results instantly
    pywebview.api.search_movies(query, appState.searchFilter)
        .then(localRes => {
            if (appState.searchQuery.trim() === query) {
                appState.movies = localRes || [];
                renderMovies();
            }
        }).catch(err => console.error(err));

    searchDebounceTimeout = setTimeout(async () => {
        if (appState.searchQuery.trim() !== query) return;
        
        try {
            const onlineRes = await pywebview.api.search_online(query, appState.searchFilter);
            if (appState.searchQuery.trim() !== query) return;
            appState.onlineSearchResults = onlineRes || [];
        } catch (e) {
            console.error("Online search error:", e);
        } finally {
            if (appState.searchQuery.trim() === query) {
                appState.isSearchingOnline = false;
                renderMovies();
            }
        }
    }, 300);
}

// --- Normalize Movie Objects ---
function normalizeMovie(movie) {
    if (!movie) return null;
    return {
        ID: movie.ID || null,
        tmdb_id: movie.tmdb_id || movie.id || null,
        Name: movie.Name || movie.titel || movie.title || 'Unbekannt',
        Jahr: movie.Jahr || movie.jahr || (movie.release_date ? movie.release_date.split('-')[0] : null) || null,
        Regisseur: movie.Regisseur || movie.regisseur || null,
        Laufzeit_min: movie.Laufzeit_min || movie.laufzeit_min || null,
        Genre: movie.Genre || movie.genre || null,
        Filmreihe: movie.Filmreihe || movie.filmreihe || null,
        FSK: movie.FSK || movie.fsk || null,
        Produktionsfirma: movie.Produktionsfirma || movie.produktionsfirma || null,
        Produktionsland: movie.Produktionsland || movie.produktionsland || null,
        Beschreibung: movie.Beschreibung || movie.beschreibung || null,
        Schauspieler: movie.Schauspieler || movie.schauspieler || null,
        Deutsche_Synchronsprecher: movie.Deutsche_Synchronsprecher || movie.deutsche_synchronsprecher || null,
        Poster_Pfad: movie.Poster_Pfad || movie.poster_path || movie.poster_pfad || null,
        Banner_Pfad: movie.Banner_Pfad || movie.backdrop_path || movie.banner_path || movie.banner_pfad || null,
        isOnline: !movie.ID
    };
}

function renderMovies() {
    const isSearching = appState.searchQuery.trim().length > 0;
    const hasLocal = appState.movies.length > 0;
    const hasOnline = appState.onlineSearchResults.length > 0;
    const hasPopular = appState.popularMovies.length > 0;
    
    const shouldShowEmpty = !isSearching && !hasLocal && !hasPopular && !appState.isSearchingOnline;
    
    if (shouldShowEmpty) {
        dom.emptyState.style.display = 'flex';
        dom.movieGrid.style.display = 'none';
        dom.movieTableWrapper.style.display = 'none';
        return;
    } else {
        dom.emptyState.style.display = 'none';
        if (appState.viewMode === 'Galerie') {
            dom.movieGrid.style.display = 'grid';
            dom.movieTableWrapper.style.display = 'none';
        } else {
            dom.movieGrid.style.display = 'none';
            dom.movieTableWrapper.style.display = 'block';
        }
    }
    
    const filterText = appState.searchFilter === 'Alles' ? 'alles' : appState.searchFilter;
    
    if (appState.viewMode === 'Galerie') {
        dom.movieGrid.innerHTML = '';
        
        if (isSearching) {
            // Render search status banner
            const banner = document.createElement('div');
            banner.className = 'search-status-text';
            banner.innerText = `Du hast nach ${filterText} "${appState.searchQuery}" gesucht, hier sind die folgenden Ergebnisse:`;
            dom.movieGrid.appendChild(banner);
            
            // Local results
            if (hasLocal) {
                const localHeader = document.createElement('h2');
                localHeader.className = 'section-header';
                localHeader.innerText = 'Meine Bibliothek';
                dom.movieGrid.appendChild(localHeader);
                
                appState.movies.forEach(movie => {
                    dom.movieGrid.appendChild(createMovieCard(normalizeMovie(movie)));
                });
            }
            
            // Online results
            const onlineHeader = document.createElement('h2');
            onlineHeader.className = 'section-header';
            onlineHeader.innerText = 'Online-Suchergebnisse (TMDB)';
            dom.movieGrid.appendChild(onlineHeader);
            
            if (hasOnline) {
                appState.onlineSearchResults.forEach(movie => {
                    dom.movieGrid.appendChild(createMovieCard(normalizeMovie(movie)));
                });
            } else if (appState.isSearchingOnline) {
                const loadingCard = document.createElement('div');
                loadingCard.className = 'movie-card';
                loadingCard.style.pointerEvents = 'none';
                loadingCard.innerHTML = `
                    <div class="movie-card-img-container" style="display:flex;align-items:center;justify-content:center;flex-direction:column;gap:10px;">
                        <div class="spinner"></div>
                        <span style="font-size:12px;color:var(--text-secondary);">Suche auf TMDB...</span>
                    </div>
                `;
                dom.movieGrid.appendChild(loadingCard);
            } else {
                const noOnline = document.createElement('div');
                noOnline.style.gridColumn = '1 / -1';
                noOnline.style.color = 'var(--text-muted)';
                noOnline.style.fontSize = '13px';
                noOnline.innerText = 'Keine Online-Treffer gefunden.';
                dom.movieGrid.appendChild(noOnline);
            }
        } else {
            // Not searching
            if (hasLocal) {
                const localHeader = document.createElement('h2');
                localHeader.className = 'section-header';
                localHeader.innerText = 'Meine Bibliothek';
                dom.movieGrid.appendChild(localHeader);
                
                appState.movies.forEach(movie => {
                    dom.movieGrid.appendChild(createMovieCard(normalizeMovie(movie)));
                });
                
                const popularHeader = document.createElement('h2');
                popularHeader.className = 'section-header';
                popularHeader.innerText = 'Aktuell beliebte Filme';
                dom.movieGrid.appendChild(popularHeader);
                
                appState.popularMovies.forEach(movie => {
                    dom.movieGrid.appendChild(createMovieCard(normalizeMovie(movie)));
                });
            } else {
                const popularHeader = document.createElement('h2');
                popularHeader.className = 'section-header';
                popularHeader.innerText = 'Aktuell beliebte Filme';
                dom.movieGrid.appendChild(popularHeader);
                
                appState.popularMovies.forEach(movie => {
                    dom.movieGrid.appendChild(createMovieCard(normalizeMovie(movie)));
                });
            }
        }
    } else {
        // Table view
        dom.movieTableBody.innerHTML = '';
        
        if (isSearching) {
            // Render search status banner as a row
            const trBanner = document.createElement('tr');
            trBanner.style.pointerEvents = 'none';
            trBanner.innerHTML = `
                <td colspan="8">
                    <div class="search-status-text" style="margin-bottom:0;">
                        Du hast nach ${filterText} "${appState.searchQuery}" gesucht, hier sind die folgenden Ergebnisse:
                    </div>
                </td>
            `;
            dom.movieTableBody.appendChild(trBanner);
            
            // Local results
            if (hasLocal) {
                const trHeader = document.createElement('tr');
                trHeader.style.pointerEvents = 'none';
                trHeader.innerHTML = `
                    <td colspan="8" class="table-section-header">Meine Bibliothek</td>
                `;
                dom.movieTableBody.appendChild(trHeader);
                
                let localIndex = 1;
                appState.movies.forEach(movie => {
                    dom.movieTableBody.appendChild(createMovieRow(normalizeMovie(movie), localIndex++));
                });
            }
            
            // Online results
            const trOnlineHeader = document.createElement('tr');
            trOnlineHeader.style.pointerEvents = 'none';
            trOnlineHeader.innerHTML = `
                <td colspan="8" class="table-section-header">Online-Suchergebnisse (TMDB)</td>
            `;
            dom.movieTableBody.appendChild(trOnlineHeader);
            
            if (hasOnline) {
                appState.onlineSearchResults.forEach(movie => {
                    dom.movieTableBody.appendChild(createMovieRow(normalizeMovie(movie), null));
                });
            } else if (appState.isSearchingOnline) {
                const trLoading = document.createElement('tr');
                trLoading.style.pointerEvents = 'none';
                trLoading.innerHTML = `
                    <td colspan="8" style="text-align:center;padding:20px;">
                        <div style="display:inline-flex;align-items:center;gap:10px;">
                            <div class="spinner" style="width:16px;height:16px;"></div>
                            <span style="color:var(--text-secondary);font-size:13px;">Suche auf TMDB...</span>
                        </div>
                    </td>
                `;
                dom.movieTableBody.appendChild(trLoading);
            } else {
                const trNoOnline = document.createElement('tr');
                trNoOnline.style.pointerEvents = 'none';
                trNoOnline.innerHTML = `
                    <td colspan="8" style="color:var(--text-muted);font-size:13px;padding:12px 16px;">
                        Keine Online-Ergebnisse.
                    </td>
                `;
                dom.movieTableBody.appendChild(trNoOnline);
            }
        } else {
            // Not searching
            if (hasLocal) {
                const trHeader = document.createElement('tr');
                trHeader.style.pointerEvents = 'none';
                trHeader.innerHTML = `
                    <td colspan="8" class="table-section-header">Meine Bibliothek</td>
                `;
                dom.movieTableBody.appendChild(trHeader);
                
                let localIndex = 1;
                appState.movies.forEach(movie => {
                    dom.movieTableBody.appendChild(createMovieRow(normalizeMovie(movie), localIndex++));
                });
                
                const trPopularHeader = document.createElement('tr');
                trPopularHeader.style.pointerEvents = 'none';
                trPopularHeader.innerHTML = `
                    <td colspan="8" class="table-section-header">Aktuell beliebte Filme</td>
                `;
                dom.movieTableBody.appendChild(trPopularHeader);
                
                appState.popularMovies.forEach(movie => {
                    dom.movieTableBody.appendChild(createMovieRow(normalizeMovie(movie), null));
                });
            } else {
                const trPopularHeader = document.createElement('tr');
                trPopularHeader.style.pointerEvents = 'none';
                trPopularHeader.innerHTML = `
                    <td colspan="8" class="table-section-header">Aktuell beliebte Filme</td>
                `;
                dom.movieTableBody.appendChild(trPopularHeader);
                
                appState.popularMovies.forEach(movie => {
                    dom.movieTableBody.appendChild(createMovieRow(normalizeMovie(movie), null));
                });
            }
        }
    }
}

// --- Create Movie Card for Gallery ---
function createMovieCard(movie) {
    const card = document.createElement('div');
    card.className = 'movie-card';
    if (movie.isOnline) {
        card.classList.add('online-card');
        card.addEventListener('click', () => showOnlineMovieDetails(movie.tmdb_id, movie.Name));
    } else {
        card.addEventListener('click', () => showMovieDetails(movie));
    }

    const imgContainer = document.createElement('div');
    imgContainer.className = 'movie-card-img-container';

    let src = '';
    if (movie.Poster_Pfad) {
        const isTmdbPath = movie.Poster_Pfad.startsWith('/') && !movie.Poster_Pfad.includes(':/') && !movie.Poster_Pfad.includes('assets/') && !movie.Poster_Pfad.startsWith('/media/');
        if (isTmdbPath) {
            src = `https://image.tmdb.org/t/p/w342${movie.Poster_Pfad}`;
        } else {
            src = getMediaUrl(movie.Poster_Pfad);
        }
    }

    if (src) {
        const img = document.createElement('img');
        img.src = src;
        img.className = 'movie-card-img';
        img.alt = movie.Name;
        img.onerror = () => {
            imgContainer.innerHTML = getPlaceholderHtml(movie.Name);
        };
        imgContainer.appendChild(img);
    } else {
        imgContainer.innerHTML = getPlaceholderHtml(movie.Name);
    }

    if (movie.isOnline) {
        const overlay = document.createElement('div');
        overlay.className = 'import-overlay';
        overlay.innerHTML = `
            <button class="btn btn-primary btn-glow btn-import-card" style="display: inline-flex; align-items: center; justify-content: center; gap: 6px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Importieren
            </button>
        `;
        overlay.querySelector('.btn-import-card').addEventListener('click', (e) => {
            e.stopPropagation();
            importMovie(movie.tmdb_id, movie.Name);
        });
        imgContainer.appendChild(overlay);
    }

    const meta = document.createElement('div');
    meta.className = 'movie-card-meta';
    
    const title = document.createElement('div');
    title.className = 'movie-card-title';
    title.innerText = movie.Name;

    const year = document.createElement('div');
    year.className = 'movie-card-year';
    year.innerText = movie.Jahr || 'k.A.';

    meta.appendChild(title);
    meta.appendChild(year);
    card.appendChild(imgContainer);
    card.appendChild(meta);
    return card;
}

// --- Create Movie Row for Table ---
function createMovieRow(movie, displayIndex) {
    const tr = document.createElement('tr');
    if (movie.isOnline) {
        tr.classList.add('online-row');
        tr.addEventListener('click', (e) => {
            if (e.target.closest('.table-actions')) return;
            showOnlineMovieDetails(movie.tmdb_id, movie.Name);
        });
    } else {
        tr.addEventListener('click', (e) => {
            if (e.target.closest('.table-actions')) return;
            showMovieDetails(movie);
        });
    }

    const idText = (movie.isOnline || displayIndex === null || displayIndex === undefined) ? '—' : String(displayIndex).padStart(2, '0');
    
    tr.innerHTML = `
        <td>${idText}</td>
        <td style="font-weight: 600;">${movie.Name}</td>
        <td>${movie.Jahr || 'k.A.'}</td>
        <td>${movie.Regisseur || '—'}</td>
        <td>${movie.Genre || '—'}</td>
        <td>${movie.Laufzeit_min ? movie.Laufzeit_min + ' Min.' : '—'}</td>
        <td>${movie.Filmreihe || '—'}</td>
        <td>
            <div class="table-actions">
                ${movie.isOnline ? `
                    <button class="table-action-btn import-row-btn" style="color: var(--accent); font-weight: bold; border: 1px solid var(--accent); border-radius: 4px; padding: 4px 8px; display: inline-flex; align-items: center; gap: 4px;">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Import
                    </button>
                ` : `
                    <button class="table-action-btn delete-row-btn" title="Löschen">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                `}
            </div>
        </td>
    `;

    if (movie.isOnline) {
        tr.querySelector('.import-row-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            importMovie(movie.tmdb_id, movie.Name);
        });
    } else {
        tr.querySelector('.delete-row-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteMovie(movie.ID);
        });
    }

    return tr;
}

function getPlaceholderHtml(title) {
    return `
        <div class="movie-card-placeholder">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
            <span>${title}</span>
        </div>
    `;
}

function getMediaUrl(dbPath) {
    if (!dbPath) return '';
    if (dbPath.startsWith('http://') || dbPath.startsWith('https://')) {
        return dbPath;
    }
    const normalized = dbPath.replace(/\\/g, '/');
    const lower = normalized.toLowerCase();
    
    if (lower.includes('/posters/')) {
        const idx = lower.indexOf('/posters/');
        return '/media/posters/' + normalized.substring(idx + 9);
    }
    if (lower.includes('/banners/')) {
        const idx = lower.indexOf('/banners/');
        return '/media/banners/' + normalized.substring(idx + 9);
    }
    
    // Fallback patterns
    const posterKeyword = 'posters/';
    const bannerKeyword = 'banners/';
    if (lower.includes(posterKeyword)) {
        const idx = lower.indexOf(posterKeyword);
        return '/media/posters/' + normalized.substring(idx + posterKeyword.length);
    }
    if (lower.includes(bannerKeyword)) {
        const idx = lower.indexOf(bannerKeyword);
        return '/media/banners/' + normalized.substring(idx + bannerKeyword.length);
    }
    
    return dbPath;
}

// --- Detail View modal logic ---
function showMovieDetails(movie) {
    appState.currentMovie = movie;
    
    document.getElementById('detail-title').innerText = movie.Name;
    document.getElementById('detail-tagline').innerText = movie.Filmreihe ? `Teil der Reihe: ${movie.Filmreihe}` : '';
    document.getElementById('detail-year').innerText = `Jahr: ${movie.Jahr || 'k.A.'}`;
    document.getElementById('detail-runtime').innerText = `Laufzeit: ${movie.Laufzeit_min || '-'} min`;
    
    const fskTag = document.getElementById('detail-fsk');
    const fskLogo = document.getElementById('detail-fsk-logo');
    const validFsks = ["0", "6", "12", "16", "18"];
    let fskStr = movie.FSK ? String(movie.FSK).replace("FSK", "").trim() : "";
    
    if (fskStr && validFsks.includes(fskStr)) {
        fskLogo.src = `/assets/fsk/fsk${fskStr}.png`;
        fskLogo.style.display = 'inline-block';
        fskTag.style.display = 'none';
    } else if (movie.FSK) {
        fskTag.innerText = `FSK ${movie.FSK}`;
        fskTag.style.display = 'inline-block';
        fskLogo.style.display = 'none';
    } else {
        fskTag.style.display = 'none';
        fskLogo.style.display = 'none';
    }
    
    document.getElementById('detail-country').innerText = `Land: ${movie.Produktionsland || 'k.A.'}`;
    document.getElementById('detail-description').innerText = movie.Beschreibung || 'Keine Beschreibung vorhanden.';
    document.getElementById('detail-director').innerText = movie.Regisseur || 'k.A.';
    document.getElementById('detail-series').innerText = movie.Filmreihe || '—';
    document.getElementById('detail-genre').innerText = movie.Genre || 'k.A.';
    document.getElementById('detail-studio').innerText = movie.Produktionsfirma || 'k.A.';
    document.getElementById('detail-cast').innerText = movie.Schauspieler || 'Keine Angaben.';
    document.getElementById('detail-voices').innerText = movie.Deutsche_Synchronsprecher || 'Keine Angaben.';

    // Banner and Poster URLs
    const bannerEl = document.getElementById('detail-banner');
    const btnDownloadBanner = document.getElementById('btn-download-banner');
    const btnChangeBanner = document.getElementById('btn-change-banner');
    const bannerPlaceholder = document.getElementById('detail-banner-placeholder');
    const bannerContainer = document.getElementById('detail-banner-container');
    
    // Clear old event listeners by cloning
    const newChangeBanner = btnChangeBanner.cloneNode(true);
    btnChangeBanner.parentNode.replaceChild(newChangeBanner, btnChangeBanner);
    
    const newPlaceholder = bannerPlaceholder.cloneNode(true);
    bannerPlaceholder.parentNode.replaceChild(newPlaceholder, bannerPlaceholder);

    if (movie.Banner_Pfad) {
        const isTmdbPath = movie.Banner_Pfad.startsWith('/') && !movie.Banner_Pfad.includes(':/') && !movie.Banner_Pfad.includes('assets/') && !movie.Banner_Pfad.startsWith('/media/');
        if (isTmdbPath) {
            bannerEl.src = `https://image.tmdb.org/t/p/w780${movie.Banner_Pfad}`;
        } else {
            bannerEl.src = getMediaUrl(movie.Banner_Pfad);
        }
        
        bannerEl.style.display = 'block';
        newPlaceholder.style.display = 'none';
        bannerContainer.style.display = 'flex';
        
        btnDownloadBanner.style.display = movie.isOnline ? 'none' : 'block';
        newChangeBanner.style.display = movie.isOnline ? 'none' : 'block';
        
        if (!movie.isOnline) {
            newChangeBanner.addEventListener('click', () => changeBanner(movie));
        }
    } else {
        bannerEl.src = '';
        bannerEl.style.display = 'none';
        
        if (movie.isOnline) {
            bannerContainer.style.display = 'none';
            btnDownloadBanner.style.display = 'none';
            newChangeBanner.style.display = 'none';
            newPlaceholder.style.display = 'none';
        } else {
            bannerContainer.style.display = 'flex';
            newPlaceholder.style.display = 'flex';
            btnDownloadBanner.style.display = 'none';
            newChangeBanner.style.display = 'none';
            newPlaceholder.addEventListener('click', () => changeBanner(movie));
        }
    }

    const posterEl = document.getElementById('detail-poster');
    const btnDownloadPoster = document.getElementById('btn-download-poster');
    if (movie.Poster_Pfad) {
        const isTmdbPath = movie.Poster_Pfad.startsWith('/') && !movie.Poster_Pfad.includes(':/') && !movie.Poster_Pfad.includes('assets/') && !movie.Poster_Pfad.startsWith('/media/');
        if (isTmdbPath) {
            posterEl.src = `https://image.tmdb.org/t/p/w342${movie.Poster_Pfad}`;
        } else {
            posterEl.src = getMediaUrl(movie.Poster_Pfad);
        }
        posterEl.style.display = 'block';
        btnDownloadPoster.style.display = movie.isOnline ? 'none' : 'block';
    } else {
        posterEl.src = '';
        posterEl.style.display = 'none';
        btnDownloadPoster.style.display = 'none';
    }

    // Discord description textarea
    const discordPreviewBlock = document.getElementById('discord-preview-block');
    const discordInput = document.getElementById('discord-description-input');
    if (!movie.isOnline) {
        discordInput.value = generateDiscordText(movie);
        discordPreviewBlock.style.display = 'block';
    } else {
        discordPreviewBlock.style.display = 'none';
    }

    // Configure footer actions
    const footerActions = document.querySelector('.detail-footer-actions');
    if (movie.isOnline) {
        footerActions.innerHTML = `
            <button id="btn-import-current" class="btn btn-primary btn-glow" style="width: 100%; display: inline-flex; align-items: center; justify-content: center; gap: 6px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Film importieren
            </button>
        `;
        document.getElementById('btn-import-current').addEventListener('click', () => {
            importMovie(movie.tmdb_id, movie.Name);
        });
    } else {
        footerActions.innerHTML = `
            <button id="btn-copy-discord" class="btn btn-primary btn-glow" style="background: #5865F2; color: white; border: none; box-shadow: 0 0 12px rgba(88, 101, 242, 0.4); display: inline-flex; align-items: center; justify-content: center; gap: 6px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                Discord-Text kopieren
            </button>
            <button id="btn-delete-current" class="btn btn-danger">Löschen</button>
        `;
        document.getElementById('btn-copy-discord').addEventListener('click', () => {
            copyEditedDiscordText();
        });
        document.getElementById('btn-delete-current').addEventListener('click', () => {
            deleteMovie(movie.ID);
        });
    }

    openModal('modal-details');
}

// --- Import movie directly from search or details modal ---
async function importMovie(tmdbId, movieName) {
    showLoading(`Importiere '${movieName}'...`);
    try {
        const details = await pywebview.api.get_movie_details(tmdbId);
        if (!details) {
            showCustomAlert("Filmdetails konnten nicht geladen werden.", "Importfehler");
            hideLoading();
            return;
        }
        
        const movieData = {
            tmdb_id: tmdbId,
            Name: details.titel || movieName,
            Jahr: details.jahr ? parseInt(details.jahr) : null,
            Regisseur: details.regisseur || null,
            Laufzeit_min: details.laufzeit_min ? parseInt(details.laufzeit_min) : null,
            Genre: details.genre_richtung || details.genre || null,
            Filmreihe: details.filmreihe || null,
            FSK: details.fsk || null,
            Produktionsfirma: details.produktionsfirma_studio || details.produktionsfirma || null,
            Produktionsland: details.produktionsland || null,
            Beschreibung: details.handlung_beschreibung || details.beschreibung || null,
            Schauspieler: details.schauspieler_cast || details.schauspieler || null,
            Deutsche_Synchronsprecher: details.deutsche_synchronsprecher || null,
            Poster_Pfad: details.poster_pfad || details.poster_path || null,
            Banner_Pfad: details.banner_pfad || details.backdrop_path || null
        };
        
        const res = await pywebview.api.add_movie(movieData);
        hideLoading();
        
        if (res.success) {
            showCustomAlert(`'${movieName}' wurde erfolgreich importiert!`, "Import erfolgreich");
            closeModal('modal-details');
            
            // Refresh
            if (appState.searchQuery.trim().length > 0) {
                performSearch();
            } else {
                await refreshMovies();
            }
        } else {
            showCustomAlert("Fehler beim Importieren: " + res.error, "Importfehler");
        }
    } catch (e) {
        console.error("Import failed:", e);
        hideLoading();
    }
}

// --- Show details for an online/popular movie ---
async function showOnlineMovieDetails(tmdbId, movieName) {
    showLoading("Lade Filminformationen...");
    try {
        const details = await pywebview.api.get_movie_details(tmdbId);
        hideLoading();
        if (details) {
            const normalized = normalizeMovie({
                id: tmdbId,
                titel: details.titel || movieName,
                jahr: details.jahr || '',
                regisseur: details.regisseur || '',
                laufzeit_min: details.laufzeit_min || '',
                genre: details.genre_richtung || details.genre || '',
                filmreihe: details.filmreihe || '',
                fsk: details.fsk || '',
                produktionsfirma: details.produktionsfirma_studio || details.produktionsfirma || '',
                produktionsland: details.produktionsland || '',
                beschreibung: details.handlung_beschreibung || details.beschreibung || '',
                schauspieler: details.schauspieler_cast || details.schauspieler || '',
                deutsche_synchronsprecher: details.deutsche_synchronsprecher || '',
                poster_path: details.poster_pfad || details.poster_path || '',
                backdrop_path: details.banner_pfad || details.backdrop_path || ''
            });
            showMovieDetails(normalized);
        } else {
            showCustomAlert("Filmdetails konnten nicht geladen werden.", "Fehler");
        }
    } catch (e) {
        console.error("Failed loading online details:", e);
        hideLoading();
    }
}

// --- Discord embed text formatting & copying ---
function generateDiscordText(movie) {
    const titel = movie.Name || 'Unbekannt';
    const jahr = movie.Jahr;
    const jahrStr = jahr ? ` (${jahr})` : '';
    const genres = movie.Genre || 'k.A.';
    const laufzeit = movie.Laufzeit_min || 0;
    const fsk = movie.FSK ? `ab ${movie.FSK}` : 'k.A.';
    const regisseur = movie.Regisseur || 'k.A.';
    const cast = (movie.Schauspieler || 'k.A.').trim();
    const beschreibung = (movie.Beschreibung || 'Keine Beschreibung vorhanden.').trim();
    const filmreihe = (movie.Filmreihe || '').trim();
    const studio = movie.Produktionsfirma || 'k.A.';
    const land = movie.Produktionsland || 'k.A.';
    const synchronsprecher = (movie.Deutsche_Synchronsprecher || '').trim();

    const castFormatted = cast.split('\n').map(line => `> ${line}`).join('\n');
    const descFormatted = beschreibung.split('\n').map(line => `> ${line}`).join('\n');

    let lines = [
        `**🎬 CinePalast Film-Tipp: ${titel}${jahrStr}**`,
        `> **Genre:** ${genres} | **Laufzeit:** ${laufzeit} Min. | **FSK:** ${fsk}`,
        `> **Regisseur:** ${regisseur} | **Studio:** ${studio} | **Land:** ${land}`
    ];

    if (filmreihe && filmreihe !== '-') {
        lines.push(`> **Filmreihe:** ${filmreihe}`);
    }

    lines.push(`> **Besetzung:**`);
    lines.push(castFormatted);

    if (synchronsprecher && synchronsprecher !== '-') {
        const syncFormatted = synchronsprecher.split('\n').map(line => `> ${line}`).join('\n');
        lines.push(`> **Deutsche Stimmen:**`);
        lines.push(syncFormatted);
    }

    lines.push(`>`);
    lines.push(`> 📝 **Handlung & Beschreibung:**`);
    lines.push(descFormatted);
    lines.push(`>`);
    lines.push(`> *Gesendet aus dem CinePalast Manager von Mannis Kinopalast*`);

    let text = lines.join('\n');
    if (text.length > 1990) {
        text = text.substring(0, 1987) + '...';
    }
    return text;
}

async function copyDiscordText(movie) {
    const text = generateDiscordText(movie);
    try {
        await navigator.clipboard.writeText(text);
        showCustomAlert("Die Discord-Beschreibung wurde erfolgreich in Ihre Zwischenablage kopiert!", "Discord-Text kopiert");
    } catch (err) {
        console.error('Failed to copy text: ', err);
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showCustomAlert("Die Discord-Beschreibung wurde erfolgreich kopiert!", "Discord-Text kopiert");
    }
}

async function copyEditedDiscordText() {
    const text = document.getElementById('discord-description-input').value;
    try {
        await navigator.clipboard.writeText(text);
        showCustomAlert("Die Discord-Beschreibung wurde erfolgreich in Ihre Zwischenablage kopiert!", "Discord-Text kopiert");
    } catch (err) {
        console.error('Failed to copy text: ', err);
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showCustomAlert("Die Discord-Beschreibung wurde erfolgreich kopiert!", "Discord-Text kopiert");
    }
}

// --- Save Poster/Banner to Desktop ---
async function downloadPoster(movie) {
    if (!movie.Poster_Pfad) return;
    showLoading("Speichere Poster...");
    try {
        const res = await pywebview.api.download_image_to_desktop(movie.Name, movie.Poster_Pfad, 'poster');
        hideLoading();
        if (res.success) {
            showCustomAlert(`Das Film-Poster wurde auf Ihrem Desktop gespeichert als:\n\n${res.filename}`, "Poster gespeichert");
        } else {
            showCustomAlert("Fehler beim Speichern: " + res.error, "Fehler");
        }
    } catch (e) {
        console.error(e);
        hideLoading();
    }
}

async function downloadBanner(movie) {
    if (!movie.Banner_Pfad) return;
    showLoading("Speichere Banner...");
    try {
        const res = await pywebview.api.download_image_to_desktop(movie.Name, movie.Banner_Pfad, 'banner');
        hideLoading();
        if (res.success) {
            showCustomAlert(`Das Filmbanner wurde auf Ihrem Desktop gespeichert als:\n\n${res.filename}`, "Banner gespeichert");
        } else {
            showCustomAlert("Fehler beim Speichern: " + res.error, "Fehler");
        }
    } catch (e) {
        console.error(e);
        hideLoading();
    }
}

async function changeBanner(movie) {
    try {
        const filePath = await pywebview.api.select_image_file();
        if (filePath) {
            showLoading("Kopiere Banner...");
            const res = await pywebview.api.copy_image_to_media(filePath, 'banner');
            hideLoading();
            
            if (res.success) {
                showLoading("Speichere Banner...");
                const dbRes = await pywebview.api.update_movie(movie.ID, { "Banner_Pfad": res.path });
                hideLoading();
                
                if (dbRes.success) {
                    showCustomAlert("Das Filmbanner wurde erfolgreich aktualisiert!", "Erfolg");
                    movie.Banner_Pfad = res.path;
                    await refreshMovies();
                    showMovieDetails(movie);
                } else {
                    showCustomAlert("Fehler beim Speichern in der Datenbank: " + dbRes.error, "Fehler");
                }
            } else {
                showCustomAlert("Fehler beim Kopieren des Bildes: " + res.error, "Fehler");
            }
        }
    } catch (e) {
        console.error("Change banner error:", e);
        hideLoading();
    }
}

// --- Trigger online search if no local matches found ---
async function triggerOnlineSearch() {
    if (!appState.searchQuery.trim()) return;
    
    showLoading("Suche online auf TMDB...");
    try {
        appState.onlineSearchResults = await pywebview.api.search_online(appState.searchQuery, appState.searchFilter);
        renderMovies();
    } catch (e) {
        console.error("Online search failed:", e);
    } finally {
        hideLoading();
    }
}

// --- Open Movie Add/Edit Form ---
function openMovieForm(movie = null) {
    const isEdit = !!movie;
    document.getElementById('movie-form-title').innerText = isEdit ? (movie.ID ? "Film bearbeiten" : "Film hinzufügen") : "Film hinzufügen";
    
    document.getElementById('form-movie-id').value = (movie && movie.ID) || '';
    document.getElementById('form-tmdb-id').value = (movie && movie.tmdb_id) || '';
    
    document.getElementById('form-title').value = (movie && movie.Name) || '';
    document.getElementById('form-year').value = (movie && movie.Jahr) || '';
    document.getElementById('form-director').value = (movie && movie.Regisseur) || '';
    document.getElementById('form-runtime').value = (movie && movie.Laufzeit_min) || '';
    document.getElementById('form-genre').value = (movie && movie.Genre) || '';
    document.getElementById('form-series').value = (movie && movie.Filmreihe) || '';
    document.getElementById('form-fsk').value = (movie && movie.FSK) || '';
    document.getElementById('form-studio').value = (movie && movie.Produktionsfirma) || '';
    document.getElementById('form-country').value = (movie && movie.Produktionsland) || '';
    document.getElementById('form-description').value = (movie && movie.Beschreibung) || '';
    document.getElementById('form-cast').value = (movie && movie.Schauspieler) || '';
    document.getElementById('form-voices').value = (movie && movie.Deutsche_Synchronsprecher) || '';
    
    document.getElementById('form-poster').value = (movie && movie.Poster_Pfad) || '';
    document.getElementById('form-banner').value = (movie && movie.Banner_Pfad) || '';
    
    openModal('modal-movie-form');
}

// --- Browse file for poster/banner ---
async function browseAsset(imgType) {
    try {
        const filePath = await pywebview.api.select_image_file();
        if (filePath) {
            showLoading("Kopiere Bild...");
            const res = await pywebview.api.copy_image_to_media(filePath, imgType);
            hideLoading();
            
            if (res.success) {
                document.getElementById(`form-${imgType}`).value = res.path;
            } else {
                showCustomAlert("Fehler beim Kopieren: " + res.error, "Kopierfehler");
            }
        }
    } catch (e) {
        console.error("Browse asset failed:", e);
        hideLoading();
    }
}

// --- Submit Movie Form ---
async function submitMovieForm(event) {
    event.preventDefault();
    
    const movieId = document.getElementById('form-movie-id').value;
    const tmdbId = document.getElementById('form-tmdb-id').value;
    
    const movieData = {
        tmdb_id: tmdbId || null,
        Name: document.getElementById('form-title').value,
        Jahr: parseInt(document.getElementById('form-year').value) || null,
        Regisseur: document.getElementById('form-director').value || null,
        Laufzeit_min: parseInt(document.getElementById('form-runtime').value) || null,
        Genre: document.getElementById('form-genre').value || null,
        Filmreihe: document.getElementById('form-series').value || null,
        FSK: document.getElementById('form-fsk').value || null,
        Produktionsfirma: document.getElementById('form-studio').value || null,
        Produktionsland: document.getElementById('form-country').value || null,
        Beschreibung: document.getElementById('form-description').value || null,
        Schauspieler: document.getElementById('form-cast').value || null,
        Deutsche_Synchronsprecher: document.getElementById('form-voices').value || null,
        Poster_Pfad: document.getElementById('form-poster').value || null,
        Banner_Pfad: document.getElementById('form-banner').value || null
    };
    
    showLoading("Speichere Film...");
    try {
        let res;
        if (movieId) {
            res = await pywebview.api.update_movie(parseInt(movieId), movieData);
        } else {
            res = await pywebview.api.add_movie(movieData);
        }
        
        hideLoading();
        if (res.success) {
            closeModal('modal-movie-form');
            await refreshMovies();
            closeModal('modal-details');
        } else {
            showCustomAlert("Fehler beim Speichern: " + res.error, "Speicherfehler");
        }
    } catch (e) {
        console.error("Saving movie failed:", e);
        hideLoading();
    }
}

// --- Delete movie from database ---
async function deleteMovie(movieId) {
    const confirmed = await showCustomConfirm("Möchten Sie diesen Film wirklich dauerhaft löschen?");
    if (!confirmed) return;
    
    showLoading("Lösche Film...");
    try {
        const res = await pywebview.api.delete_movie(movieId);
        hideLoading();
        if (res.success) {
            closeModal('modal-details');
            await refreshMovies();
        } else {
            showCustomAlert("Fehler beim Löschen: " + res.error, "Fehler");
        }
    } catch (e) {
        console.error("Deleting failed:", e);
        hideLoading();
    }
}

// --- Settings Overlay Functions ---
function openSettings() {
    document.getElementById('settings-tmdb-key').value = appState.config.api_key || '';
    document.getElementById('settings-github-token').value = appState.config.github_token || '';
    document.getElementById('settings-theme').value = appState.config.theme || 'cyan';
    document.getElementById('settings-view').value = appState.config.default_view || 'Galerie';
    document.getElementById('settings-path').value = appState.config.custom_media_path || '';
    
    openModal('modal-settings');
}

async function browseCustomPath() {
    try {
        const folder = await pywebview.api.select_folder();
        if (folder) {
            document.getElementById('settings-path').value = folder;
        }
    } catch (e) {
        console.error("Browse path error:", e);
    }
}

async function testAPIConnections() {
    const tmdbKey = document.getElementById('settings-tmdb-key').value.trim();
    const ghToken = document.getElementById('settings-github-token').value.trim();
    
    showLoading("Verbindungen werden getestet...");
    
    let tmdbOk = false;
    let ghOk = false;
    
    // Test TMDB
    if (tmdbKey) {
        try {
            const url = "https://api.themoviedb.org/3/configuration";
            const headers = tmdbKey.length > 50 || tmdbKey.startsWith("eyJ") ? 
                {"Authorization": `Bearer ${tmdbKey}`} : {};
            const params = tmdbKey.length > 50 || tmdbKey.startsWith("eyJ") ? 
                {} : {"api_key": tmdbKey};
                
            const fullUrl = url + (params.api_key ? `?api_key=${params.api_key}` : '');
            const options = headers.Authorization ? { headers } : {};
            const resp = await fetch(fullUrl, options);
            if (resp.status === 200) tmdbOk = true;
        } catch(e) {}
    } else {
        tmdbOk = true; 
    }

    // Test GitHub
    if (ghToken) {
        try {
            const resp = await fetch("https://api.github.com/repos/TentixTV/CinepalastManager", {
                headers: {"Authorization": `token ${ghToken}`}
            });
            if (resp.status === 200) ghOk = true;
        } catch(e) {}
    } else {
        ghOk = true;
    }
    
    hideLoading();
    if (tmdbOk && ghOk) {
        showCustomAlert("Verbindungstest erfolgreich!", "Verbindungstest");
    } else {
        showCustomAlert(`Verbindungstest fehlgeschlagen:\nTMDB: ${tmdbOk ? 'OK' : 'Fehler'}\nGitHub: ${ghOk ? 'OK' : 'Fehler'}`, "Verbindungstest");
    }
}

async function saveSettings(event) {
    event.preventDefault();
    
    const newPath = document.getElementById('settings-path').value.trim();
    const oldPath = appState.config.custom_media_path || '';
    
    const newConfig = {
        api_key: document.getElementById('settings-tmdb-key').value.trim(),
        github_token: document.getElementById('settings-github-token').value.trim(),
        theme: document.getElementById('settings-theme').value,
        default_view: document.getElementById('settings-view').value,
        custom_media_path: newPath
    };
    
    // Do not copy existing files, only future files will be saved in the new path
    
    showLoading("Speichere Einstellungen...");
    try {
        const res = await pywebview.api.save_config(newConfig);
        hideLoading();
        
        if (res.success) {
            appState.config = newConfig;
            applyTheme(newConfig.theme);
            setViewMode(newConfig.default_view);
            closeModal('modal-settings');
            await refreshMovies();
        } else {
            showCustomAlert("Fehler beim Speichern der Einstellungen: " + res.error, "Speicherfehler");
        }
    } catch(e) {
        console.error("Save settings error:", e);
        hideLoading();
    }
}

async function backupDatabase() {
    try {
        const res = await pywebview.api.backup_database();
        if (res.success) {
            showCustomAlert("Backup erfolgreich gespeichert unter:\n" + res.path, "Backup erfolgreich");
        } else if (res.error) {
            showCustomAlert("Backup fehlgeschlagen: " + res.error, "Backupfehler");
        }
    } catch (e) {
        console.error(e);
    }
}

async function restoreDatabase() {
    const confirmed = await showCustomConfirm("ACHTUNG: Beim Laden eines Backups wird die aktuelle Datenbank überschrieben. Fortfahren?");
    if (!confirmed) return;
    
    showLoading("Backup wird geladen...");
    try {
        const res = await pywebview.api.restore_database();
        hideLoading();
        if (res.success) {
            showCustomAlert("Datenbank erfolgreich wiederhergestellt!", "Erfolg");
            closeModal('modal-settings');
            await refreshMovies();
        } else if (res.error) {
            showCustomAlert("Wiederherstellung fehlgeschlagen: " + res.error, "Wiederherstellungsfehler");
        }
    } catch(e) {
        console.error(e);
        hideLoading();
    }
}

async function resetDatabase() {
    const confirmed = await showCustomConfirm("ACHTUNG: Möchten Sie wirklich alle Filme unwiderruflich aus der Datenbank löschen?");
    if (!confirmed) return;
    
    showLoading("Setze Datenbank zurück...");
    try {
        const res = await pywebview.api.reset_database();
        hideLoading();
        if (res.success) {
            showCustomAlert("Datenbank erfolgreich geleert!", "Erfolg");
            closeModal('modal-settings');
            await refreshMovies();
        } else {
            showCustomAlert("Fehler: " + res.error, "Fehler");
        }
    } catch(e) {
        console.error(e);
        hideLoading();
    }
}

// --- Generic Modal helpers ---
function openModal(id) {
    const modal = document.getElementById(id);
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('active');
    }, 10);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove('active');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 250);
}
