# -*- coding: utf-8 -*-
import sys

with open('css/classroom.css', 'rb') as f:
    content = f.read()

# The :root block we want to replace
old_block = b"""/* ============================================================
   CSS Variables - Enhanced Design System
   ============================================================ */
:root {
  /* Primary - Warm copper gradient */
    --primary: var(--brand-500);
  --primary-light: var(--brand-400);
  --primary-dark: var(--brand-600);
  /* Accent - Rich amber */
    --accent: var(--accent-500);
  --accent-light: var(--accent-light);
  --accent-glow: rgba(217, 119, 6, 0.5);
  /* Semantic Colors */
    --success: #10b981;
  --success-light: #34d399;
  --warning-light: #fbbf24;
  --danger-light: #f87171;
  /* Background - Deep space theme */
    --bg-primary: var(--surface-page);
  --bg-secondary: var(--surface-card);
  --bg-tertiary: var(--surface-elevated);
  /* Glass surfaces */
    --glass-bg: var(--surface-glass);
  --glass-bg-hover: var(--surface-glass-hover);
  --glass-border: var(--border-glass);
  /* Surface */
    --surface-white: rgba(255, 255, 255, 0.95);
  --surface-glass-strong: rgba(255, 255, 255, 0.08);
  /* Text hierarchy */
    --text-primary: var(--text-heading);
  --text-secondary: var(--text-muted);
  --text-tertiary: #64748b;
  /* Border */
    --border-glass: rgba(255, 255, 255, 0.06);
  --border-light: rgba(255, 255, 255, 0.1);
  --border-focus: var(--primary);
  /* Shadows */
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
  --shadow-glow-primary: 0 0 40px var(--primary-glow);
  --shadow-glow-accent: 0 0 40px var(--accent-glow);
  /* Slide-specific */
    --slide-shadow: 0 8px 40px rgba(234, 88, 12, 0.3), 0 0 80px rgba(217, 119, 6, 0.2);
  --teacher-glow: 0 0 60px rgba(234, 88, 12, 0.6);
  /* Spacing */
    --sidebar-width: 72px;
  --chat-width: 320px;
  --header-height: 64px;
  --controls-height: 64px;
  /* Radius */
    --radius-sm: 8px;
  /* Transitions */
    --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  /* Z-index */
    --z-sidebar: 50;
  --z-header: 100;
  /* ============================================================
       Discussion Participant Role Colors
       ============================================================ */
    /* AI Teacher - Purple-blue */
    --role-teacher-bg: rgba(234, 88, 12, 0.15);
  --role-teacher-border: rgba(234, 88, 12, 0.4);
  --role-teacher-accent: #f97316;
  --avatar-gradient-teacher: linear-gradient(135deg, #ea580c, #d97706);
  /* Student - Teal */
    --role-student-bg: rgba(45, 212, 191, 0.12);
  --role-student-border: rgba(45, 212, 191, 0.35);
  --role-student-accent: #2dd4bf;
  --avatar-gradient-student: linear-gradient(135deg, #14b8a6, #2dd4bf);
  /* AI Agent - Indigo */
    --role-agent-bg: rgba(217, 119, 6, 0.12);
  --role-agent-border: rgba(217, 119, 6, 0.35);
  --role-agent-accent: #f59e0b;
  --avatar-gradient-agent: linear-gradient(135deg, #d97706, #f59e0b);
  /* Moderator - Slate */
    --role-moderator-bg: rgba(100, 116, 139, 0.12);
  --role-moderator-border: rgba(100, 116, 139, 0.35);
  --role-moderator-accent: #94a3b8;
  --avatar-gradient-moderator: linear-gradient(135deg, #64748b, #94a3b8);
  /* User's own messages */
    --role-user-gradient: linear-gradient(135deg, rgba(234, 88, 12, 0.2), rgba(217, 119, 6, 0.15));
  --role-user-border: rgba(234, 88, 12, 0.4);
  /* System messages */
    --role-system-bg: rgba(245, 158, 11, 0.08);
  --role-system-border: rgba(245, 158, 11, 0.2);
  --role-system-text: #fbbf24;
  /* Discussion shadows */
    --discussion-shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.25);
    --discussion-shadow-glow: 0 0 30px rgba(234, 88, 12, 0.2)
}"""

# Convert to CRLF (file uses CRLF)
old_block_crlf = old_block.replace(b'\n', b'\r\n')

# New block: v4 token compat layer
new_block = u"""/* ============================================================
   CSS Variables - v4 Token 兼容层
   把 v3 旧名映射到 tokens.css v4 + classroom 领域 token。
   下方规则用 v3 旧名仍能 work，主题切换时跟随 v4。
   ============================================================ */
:root {
  /* Brand -> tokens.css brand 主题色 */
    --primary: var(--brand-500);
  --primary-light: var(--brand-400);
  --primary-dark: var(--brand-600);
  --primary-glow: color-mix(in oklch, var(--brand-500), transparent 50%);
  /* Accent -> classroom 固定琥珀（不随 6 主题变化） */
    --accent: var(--classroom-accent);
  --accent-light: var(--classroom-accent-hover);
  --accent-glow: color-mix(in oklch, var(--classroom-accent), transparent 50%);
  /* Semantic Colors */
    --success: var(--success-500);
  --success-light: color-mix(in oklch, var(--success), white 30%);
  --warning-light: color-mix(in oklch, var(--warning), white 30%);
  --danger-light: color-mix(in oklch, var(--danger), white 30%);
  --info-light: color-mix(in oklch, var(--info), white 30%);
  /* Background -> 课堂专用渐变（带光晕） */
    --bg-primary: linear-gradient(180deg, var(--classroom-bg-from), var(--classroom-bg-to));
  --bg-secondary: var(--classroom-glass-bg);
  --bg-tertiary: var(--classroom-glass-bg-hover);
  /* Glass surfaces */
    --glass-bg: var(--classroom-glass-bg);
  --glass-bg-hover: var(--classroom-glass-bg-hover);
  --glass-border: var(--classroom-glass-border);
  /* Surface */
    --surface-white: rgba(255, 255, 255, 0.95);
  --surface-glass-strong: color-mix(in oklch, white, transparent 90%);
  /* Text hierarchy */
    --text-primary: var(--text-heading);
  --text-secondary: var(--text-body);
  --text-tertiary: var(--text-muted);
  /* Border */
    --border-glass: var(--classroom-glass-border);
  --border-light: var(--classroom-glass-border);
  --border-medium: color-mix(in oklch, var(--classroom-glass-border), white 30%);
  --border-dark: var(--border-color);
  --border-focus: var(--classroom-accent);
  /* Shadows */
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
  --shadow-glow-primary: 0 0 40px var(--primary-glow);
  --shadow-glow-accent: 0 0 40px var(--accent-glow);
  /* Slide-specific */
    --slide-shadow: var(--slide-shadow);
  --teacher-glow: 0 0 60px color-mix(in oklch, var(--classroom-accent), transparent 40%);
  /* Spacing */
    --sidebar-width: 72px;
  --chat-width: 320px;
  --header-height: 64px;
  --controls-height: 64px;
  /* Radius */
    --radius-sm: 8px;
  /* Transitions */
    --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  /* Z-index */
    --z-sidebar: 50;
  --z-header: 100;
  /* ============================================================
       Discussion Participant Role Colors - 5 角色头像
       引用 tokens.css 里新加的 --classroom-avatar-* 领域 token
       ============================================================ */
    /* AI Teacher - Indigo to Violet */
    --role-teacher-bg: color-mix(in oklch, var(--classroom-avatar-teacher), transparent 85%);
  --role-teacher-border: color-mix(in oklch, var(--classroom-avatar-teacher), transparent 60%);
  --role-teacher-accent: #6366f1;
  --avatar-gradient-teacher: var(--classroom-avatar-teacher);
  /* Student - Teal to Emerald */
    --role-student-bg: color-mix(in oklch, var(--classroom-avatar-student), transparent 88%);
  --role-student-border: color-mix(in oklch, var(--classroom-avatar-student), transparent 65%);
  --role-student-accent: #10b981;
  --avatar-gradient-student: var(--classroom-avatar-student);
  /* AI Agent - Amber */
    --role-agent-bg: color-mix(in oklch, var(--classroom-avatar-agent), transparent 88%);
  --role-agent-border: color-mix(in oklch, var(--classroom-avatar-agent), transparent 65%);
  --role-agent-accent: #f59e0b;
  --avatar-gradient-agent: var(--classroom-avatar-agent);
  /* Moderator - Pink */
    --role-moderator-bg: color-mix(in oklch, var(--classroom-avatar-moderator), transparent 88%);
  --role-moderator-border: color-mix(in oklch, var(--classroom-avatar-moderator), transparent 65%);
  --role-moderator-accent: #ec4899;
  --avatar-gradient-moderator: var(--classroom-avatar-moderator);
  /* User - Cyan to Blue */
    --role-user-gradient: var(--classroom-avatar-user);
  --role-user-border: color-mix(in oklch, var(--classroom-avatar-user), transparent 60%);
  /* System messages */
    --role-system-bg: color-mix(in oklch, var(--classroom-accent), transparent 92%);
  --role-system-border: color-mix(in oklch, var(--classroom-accent), transparent 80%);
  --role-system-text: var(--classroom-accent);
  /* Discussion shadows */
    --discussion-shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.25);
    --discussion-shadow-glow: 0 0 30px color-mix(in oklch, var(--classroom-accent), transparent 80%);
}"""
new_block_crlf = new_block.encode('utf-8').replace(b'\n', b'\r\n')

# Replace
if old_block_crlf in content:
    new_content = content.replace(old_block_crlf, new_block_crlf, 1)
    with open('css/classroom.css', 'wb') as f:
        f.write(new_content)
    print(u'OK: replaced {} bytes with {} bytes'.format(len(old_block_crlf), len(new_block_crlf)).encode('gbk', errors='replace').decode('gbk'))
else:
    print('NOT FOUND. checking partial...')
    start_pos = content.find(b':root {')
    if start_pos >= 0:
        depth = 0
        end = start_pos
        for i in range(start_pos, len(content)):
            if content[i:i+1] == b'{':
                depth += 1
            elif content[i:i+1] == b'}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        actual = content[start_pos:end]
        actual_lines = actual.split(b'\r\n')
        old_lines = old_block_crlf.split(b'\r\n')
        for i, (a, b) in enumerate(zip(actual_lines, old_lines)):
            if a != b:
                print('line {} diff:'.format(i))
                print('  actual: {!r}'.format(a[:80]))
                print('  old:    {!r}'.format(b[:80]))
                break
        else:
            print('lines match, but block not found - length diff: actual={} old={}'.format(len(actual_lines), len(old_lines)))
