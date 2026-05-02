/**
 * SSEParser — Manual SSE stream parser for fetch + ReadableStream.
 *
 * CRITICAL: TCP chunks can split JSON strings mid-character.
 * This parser accumulates raw text in a buffer and splits by the
 * SSE delimiter (\n\n) before attempting JSON.parse().
 * Never parse raw chunks directly.
 */
class SSEParser {
  constructor() {
    /** @type {string} Accumulated text not yet split into complete events */
    this._buffer = '';
    /** @type {string} Current event type */
    this._currentEvent = 'message';
    /** @type {string} Current event data (accumulated across multiple data: lines) */
    this._currentData = '';
  }

  /**
   * Feed a decoded string chunk into the parser.
   * @param {string} chunk — decoded text from TextDecoder
   */
  feed(chunk) {
    this._buffer += chunk;

    // Split on double-newline (SSE event terminator)
    // Keep the incomplete tail in _buffer
    const parts = this._buffer.split('\n\n');
    this._buffer = parts.pop() || '';  // last segment may be incomplete

    for (const part of parts) {
      if (!part.trim()) continue;
      this._parseBlock(part);
    }
  }

  /**
   * Parse a single complete SSE block (between \n\n delimiters).
   * @param {string} block
   */
  _parseBlock(block) {
    const lines = block.split('\n');
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        this._currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        this._currentData += line.slice(6);
      } else if (line.startsWith(':') && this._currentData === '') {
        // SSE comment (heartbeat), emit without data
      }
    }
    // Multiple data: lines are concatenated via += above.
    // Now emit the complete event.
    this._emit();
  }

  /** @private */
  _emit() {
    if (this._currentData === '') return;

    let data = this._currentData;
    try {
      data = JSON.parse(this._currentData);
    } catch (_e) {
      // If JSON parse fails, pass the raw string.
      // This handles partial/incomplete JSON gracefully.
    }

    if (typeof this.onEvent === 'function') {
      this.onEvent(this._currentEvent, data);
    }

    // Reset for next event
    this._currentEvent = 'message';
    this._currentData = '';
  }

  /**
   * Called for each complete SSE event.
   * @type {(eventType: string, data: any) => void}
   */
  onEvent(eventType, data) {
    console.log('[SSE]', eventType, data);
  }

  /**
   * Flush remaining buffer content.
   * Call when the stream ends.
   */
  flush() {
    if (this._buffer.trim()) {
      // Try to emit whatever is left
      const lines = this._buffer.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          this._currentData += line.slice(6);
        }
      }
      this._emit();
      this._buffer = '';
    }
  }
}

// Export for use by other modules (browser-compatible global)
if (typeof window !== 'undefined') {
  window.SSEParser = SSEParser;
}
