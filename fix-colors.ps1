$file = 'c:\Users\22821\PycharmProjects\Hachiware\星识\css\index.css'
$content = Get-Content $file -Raw -Encoding UTF8

$accentElements = @(
    '.score-excellent', '.score-good', '.score-medium', '.score-poor',
    '.socratic-badge', '.send-fab', '.msg-bubble-user',
    '.code-editor-toolbar .run-btn', '.code-editor-toolbar .grade-btn',
    '.glass-btn-primary', '.focus-duration-start',
    '.flow-btn-primary', '.music-ctrl-play', '.mini-ctrl-play',
    '.flow-music-ctrl-play'
)

foreach ($elem in $accentElements) {
    $escapedElem = [regex]::Escape($elem)
    $pattern = '(?m)(' + $escapedElem + '\s*\{[^}]*?)color:\s*white;'
    $replacement = '${1}color: var(--text-on-accent);'
    $content = $content -replace $pattern, $replacement
}

$content = $content -replace '(?m)(\[data-theme="sakura-falling"\]\s*\.msg-bubble-user\s*\{[^}]*?)color:\s*#fff;', '${1}color: var(--text-on-accent);'

$glassElements = @(
    '.tab-btn.active', '.textbook-reader-toolbar-left span',
    '.micro-course-player', '.music-toggle-btn', '.music-panel-title',
    '.music-panel-close:hover', '.music-ctrl-btn:hover', '.music-volume-btn:hover',
    '.focus-duration-toggle-btn', '.focus-duration-title', '.focus-duration-close:hover',
    '.focus-custom-input', '.mini-ctrl-btn:hover',
    '.flow-island-icon svg', '.flow-island-time', '.flow-island-btn:hover',
    '.flow-custom-field', '.flow-timer-time', '.flow-btn-ghost:hover',
    '.flow-audio-btn:hover', '.lightbox-close'
)

foreach ($elem in $glassElements) {
    $escapedElem = [regex]::Escape($elem)
    $pattern = '(?m)(' + $escapedElem + '\s*\{[^}]*?)color:\s*white;'
    $replacement = '${1}color: var(--text-primary);'
    $content = $content -replace $pattern, $replacement
}

$content = $content -replace '(?m)(\.music-volume-slider::-webkit-slider-thumb\s*\{[^}]*?)background:\s*white;', '${1}background: var(--text-on-accent);'
$content = $content -replace '(?m)(\.music-volume-slider::-moz-range-thumb\s*\{[^}]*?)background:\s*white;', '${1}background: var(--text-on-accent);'
$content = $content -replace '(?m)(\.toggle-switch::after\s*\{[^}]*?)background:\s*white;', '${1}background: var(--text-on-accent);'

$remainingWhite = ([regex]::Matches($content, '(?m)color:\s*(white|#fff|#ffffff);') | Measure-Object).Count
Write-Host "Remaining color: white/#fff instances: $remainingWhite"

Set-Content $file -Value $content -Encoding UTF8 -NoNewline
Write-Host 'Phase 1 complete: color: white replacements'
