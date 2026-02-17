/**
 * Ralph Loop Dashboard - Client-side SSE + UI interactions
 */

let currentEventSource = null;
let loopsPopoverOpen = false;
let loopsPollTimer = null;
let drawerOpen = false;
let projectsCache = null;

// Project Drawer Functions
function toggleProjectDrawer() {
    drawerOpen = !drawerOpen;
    const drawer = document.getElementById('project-drawer');
    const overlay = document.getElementById('project-drawer-overlay');

    if (drawerOpen) {
        drawer.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
        loadProjectsForDrawer();
    } else {
        drawer.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
    }
}

async function loadProjectsForDrawer() {
    const listEl = document.getElementById('drawer-project-list');
    if (!listEl) return;

    // Use cache if available
    if (projectsCache) {
        renderProjectsInDrawer(projectsCache);
        return;
    }

    try {
        const resp = await fetch('/api/projects');
        if (!resp.ok) throw new Error('Failed to load projects');
        const projects = await resp.json();
        projectsCache = projects;
        renderProjectsInDrawer(projects);
    } catch (err) {
        listEl.innerHTML = `<div class="px-4 py-3 text-sm text-red-400">Error loading projects</div>`;
    }
}

function renderProjectsInDrawer(projects) {
    const listEl = document.getElementById('drawer-project-list');
    if (!listEl) return;

    if (!projects || projects.length === 0) {
        listEl.innerHTML = `
            <div class="px-4 py-6 text-center">
                <div class="text-sm text-gray-400 mb-2">No projects registered</div>
                <a href="/" class="text-sm text-green-400 hover:text-green-300">Register a project</a>
            </div>
        `;
        return;
    }

    // Get current project ID from URL if on a project page
    const pathMatch = window.location.pathname.match(/\/project\/([^\/]+)/);
    const currentProjectId = pathMatch ? pathMatch[1] : null;

    let html = '';

    // Dashboard link
    const isDashboard = window.location.pathname === '/';
    html += `
        <a href="/" class="block px-4 py-2.5 text-sm ${isDashboard ? 'bg-green-900/30 text-green-300 border-r-2 border-green-500' : 'text-gray-300 hover:bg-gray-700/50 hover:text-gray-100'} transition-colors">
            Dashboard
        </a>
    `;

    // Project links
    projects.forEach(project => {
        const isActive = project.id === currentProjectId;
        html += `
            <a href="/project/${project.id}"
               class="block px-4 py-2.5 text-sm ${isActive ? 'bg-green-900/30 text-green-300 border-r-2 border-green-500' : 'text-gray-300 hover:bg-gray-700/50 hover:text-gray-100'} transition-colors">
                ${escapeHtml(project.name)}
            </a>
        `;
    });

    listEl.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Clear cache when navigating
window.addEventListener('beforeunload', () => {
    projectsCache = null;
});

function connectSSE(projectId) {
    if (currentEventSource) {
        currentEventSource.close();
    }

    const terminal = document.getElementById('terminal');
    if (terminal) {
        terminal.innerHTML = '';
    }

    const evtSource = new EventSource(`/api/projects/${projectId}/loop/stream`);
    currentEventSource = evtSource;

    evtSource.addEventListener('output', function(event) {
        const data = JSON.parse(event.data);
        appendToTerminal(data.line, data.parsed);

        // Handle parsed events
        for (const parsed of (data.parsed || [])) {
            if (parsed.type === 'iteration_start') {
                updateIterationDisplay(parsed.iteration);
            }
            if (parsed.type === 'ralph_control') {
                updateRalphControl(parsed);
            }
        }
    });

    evtSource.addEventListener('loop_started', function(event) {
        updateStatusBadge('running');
    });

    evtSource.addEventListener('loop_ended', function(event) {
        const data = JSON.parse(event.data);
        updateStatusBadge(data.status || 'completed');
        if (data.status === 'failed' && data.error) {
            appendToTerminal('--- Loop failed ---', []);
            for (const errLine of data.error.split('\n')) {
                appendToTerminal(errLine, []);
            }
        } else {
            appendToTerminal('--- Loop ended ---', []);
        }
    });

    evtSource.addEventListener('loop_stopped', function(event) {
        updateStatusBadge('stopped');
        appendToTerminal('--- Loop stopped ---', []);
        evtSource.close();
    });

    evtSource.addEventListener('ping', function(event) {
        // Keepalive, ignore
    });

    evtSource.onerror = function() {
        appendToTerminal('--- SSE connection lost, reconnecting... ---', []);
        setTimeout(() => {
            if (evtSource.readyState === EventSource.CLOSED) {
                connectSSE(projectId);
            }
        }, 3000);
    };

    return evtSource;
}

function appendToTerminal(line, parsed) {
    const terminal = document.getElementById('terminal');
    if (!terminal) return;

    // Remove placeholder text
    const placeholder = terminal.querySelector('.text-gray-500');
    if (placeholder && placeholder.textContent.includes('Waiting')) {
        placeholder.remove();
    }
    if (placeholder && placeholder.textContent.includes('Connecting')) {
        placeholder.remove();
    }

    const lineEl = document.createElement('div');

    // Apply styling based on parsed events
    let className = '';
    if (parsed && parsed.length > 0) {
        const type = parsed[0].type;
        if (type === 'iteration_start') className = 'line-iteration';
        else if (type === 'ralph_control') className = 'line-ralph-control';
        else if (type === 'all_phases_complete') className = 'line-success';
    }
    if (line.includes('Error') || line.includes('FAIL')) className = 'line-error';
    if (line.includes('complete') || line.includes('PASS')) className = 'line-success';

    lineEl.className = className;
    lineEl.textContent = line;
    terminal.appendChild(lineEl);

    // Auto-scroll to bottom
    terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminal() {
    const terminal = document.getElementById('terminal');
    if (terminal) {
        terminal.innerHTML = '<div class="text-gray-500">Terminal cleared</div>';
    }
}

function updateIterationDisplay(iteration) {
    const el = document.getElementById('iteration-display') || document.getElementById('loop-iteration');
    if (el) {
        el.textContent = iteration;
    }
}

function updateStatusBadge(status) {
    const el = document.getElementById('status-badge') || document.getElementById('loop-status');
    if (el) {
        el.textContent = status;
        el.className = `text-xs status-${status}`;
    }
}

function updateRalphControl(data) {
    const el = document.getElementById('ralph-control');
    if (el) {
        let html = '';
        for (const [key, value] of Object.entries(data)) {
            if (key === 'type') continue;
            html += `<div class="flex justify-between"><span class="text-gray-400">${key}</span><span>${value}</span></div>`;
        }
        el.innerHTML = html || 'No data';
    }
}

function formatWhen(isoString) {
    if (!isoString) return '—';
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return isoString;
    return dt.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
}

function loopProgressText(loop) {
    if (loop.max_iterations > 0) {
        const pct = loop.progress_percent == null ? 0 : loop.progress_percent;
        return `${loop.iteration}/${loop.max_iterations} (${pct}%)`;
    }
    return `${loop.iteration} (unlimited)`;
}

function renderRunningLoops(loops) {
    const list = document.getElementById('running-loops-list');
    if (!list) return;

    if (!loops || loops.length === 0) {
        list.innerHTML = '<div class="text-sm text-gray-500 px-1 py-2">No active loops.</div>';
        return;
    }

    list.innerHTML = loops.map((loop) => {
        const detailsLink = loop.kind === 'ralph_job'
            ? `/ralph/jobs/${loop.job_id}`
            : `/project/${loop.project_id}#loops`;
        const actions = (loop.recent_actions || []).slice(-3).reverse();
        const actionsHtml = actions.length > 0
            ? actions.map(a => `
                <div class="flex items-start justify-between gap-3 text-xs py-1">
                    <span class="text-gray-300 truncate">${a.message}</span>
                    <span class="text-gray-500 whitespace-nowrap">${formatWhen(a.time)}</span>
                </div>
            `).join('')
            : '<div class="text-xs text-gray-500 py-1">No recent actions yet.</div>';

        return `
            <div class="rounded-md border border-gray-700 bg-gray-800 p-3">
                <div class="flex items-center justify-between gap-2">
                    <a href="${detailsLink}" class="text-sm font-medium text-gray-100 hover:text-green-300 truncate">${loop.project_name}</a>
                    <span class="text-[11px] px-2 py-0.5 rounded border border-green-800 text-green-300">${loop.status}</span>
                </div>
                <div class="text-xs text-gray-400 mt-1 truncate">${loop.feature_name} · ${loop.mode} · ${loop.provider_display_name || loop.provider} / ${loop.model}</div>
                <div class="text-xs text-gray-300 mt-2">Progress: ${loopProgressText(loop)}</div>
                <div class="mt-2 border-t border-gray-700 pt-2">
                    <div class="text-[11px] uppercase tracking-wide text-gray-500 mb-1">Recent Actions</div>
                    ${actionsHtml}
                </div>
                <div class="mt-2 flex justify-end">
                    <button type="button" onclick='stopLoopFromNav(${JSON.stringify(loop)})'
                            class="px-2.5 py-1 text-xs rounded bg-red-900/60 hover:bg-red-900/80 border border-red-700 text-red-200 transition-colors">
                        Stop
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function updateRunningLoopsIndicator(count) {
    const button = document.getElementById('running-loops-toggle');
    const label = document.getElementById('running-loops-label');
    if (!button || !label) return;

    label.textContent = count === 1 ? '1 loop running' : `${count} loops running`;
    if (count > 0) {
        button.classList.remove('hidden');
        button.classList.add('inline-flex');
    } else {
        button.classList.add('hidden');
        button.classList.remove('inline-flex');
        const popover = document.getElementById('running-loops-popover');
        if (popover) popover.classList.add('hidden');
        loopsPopoverOpen = false;
    }
}

async function refreshRunningLoops(forceOpen = false) {
    const list = document.getElementById('running-loops-list');
    if (!list) return;

    try {
        const resp = await fetch('/api/loops/running');
        if (!resp.ok) return;
        const data = await resp.json();
        updateRunningLoopsIndicator(data.count || 0);
        renderRunningLoops(data.loops || []);
        if (forceOpen && data.count > 0) {
            const popover = document.getElementById('running-loops-popover');
            popover?.classList.remove('hidden');
            loopsPopoverOpen = true;
        }
    } catch (_err) {
        // Ignore transient polling failures.
    }
}

function toggleRunningLoopsPopover() {
    const popover = document.getElementById('running-loops-popover');
    if (!popover) return;
    loopsPopoverOpen = !loopsPopoverOpen;
    popover.classList.toggle('hidden', !loopsPopoverOpen);
    if (loopsPopoverOpen) {
        refreshRunningLoops();
    }
}

async function stopLoopFromNav(loop) {
    if (!loop) return;
    if (loop.kind === 'ralph_job' && loop.job_id) {
        await fetch(`/api/ralph/jobs/${loop.job_id}/stop`, {method: 'POST'});
    } else {
        await fetch(`/api/projects/${loop.project_id}/loop/stop`, {method: 'POST'});
    }
    await refreshRunningLoops();
}

document.addEventListener('click', (event) => {
    const popover = document.getElementById('running-loops-popover');
    const toggle = document.getElementById('running-loops-toggle');
    if (!popover || !toggle || !loopsPopoverOpen) return;
    if (popover.contains(event.target) || toggle.contains(event.target)) return;
    loopsPopoverOpen = false;
    popover.classList.add('hidden');
});

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('running-loops-list')) return;
    refreshRunningLoops();
    loopsPollTimer = setInterval(() => refreshRunningLoops(), 5000);
});
