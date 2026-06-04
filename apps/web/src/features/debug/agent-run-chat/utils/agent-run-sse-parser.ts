export interface SseFrame {
  data: string;
  event?: string;
  id?: string;
}

export class SseFrameParser {
  private buffer = '';

  push(chunk: string): SseFrame[] {
    this.buffer += chunk;
    const frames: SseFrame[] = [];
    let boundary = this.findBoundary();

    while (boundary !== -1) {
      const rawFrame = this.buffer.slice(0, boundary.index);
      this.buffer = this.buffer.slice(boundary.index + boundary.length);
      const frame = parseSseFrame(rawFrame);
      if (frame) frames.push(frame);
      boundary = this.findBoundary();
    }

    return frames;
  }

  flush(): SseFrame[] {
    if (!this.buffer.trim()) {
      this.buffer = '';
      return [];
    }
    const frame = parseSseFrame(this.buffer);
    this.buffer = '';
    return frame ? [frame] : [];
  }

  private findBoundary(): { index: number; length: number } | -1 {
    const lf = this.buffer.indexOf('\n\n');
    const crlf = this.buffer.indexOf('\r\n\r\n');

    if (lf === -1 && crlf === -1) return -1;
    if (lf === -1) return { index: crlf, length: 4 };
    if (crlf === -1) return { index: lf, length: 2 };
    return lf < crlf ? { index: lf, length: 2 } : { index: crlf, length: 4 };
  }
}

export function parseSseFrame(rawFrame: string): SseFrame | null {
  const frame: SseFrame = { data: '' };
  const dataLines: string[] = [];

  for (const line of rawFrame.split(/\r?\n/u)) {
    if (!line || line.startsWith(':')) continue;
    const separatorIndex = line.indexOf(':');
    const field = separatorIndex === -1 ? line : line.slice(0, separatorIndex);
    const value = separatorIndex === -1 ? '' : line.slice(separatorIndex + 1).replace(/^ /u, '');

    if (field === 'event') frame.event = value;
    if (field === 'id') frame.id = value;
    if (field === 'data') dataLines.push(value);
  }

  frame.data = dataLines.join('\n');
  return frame.event || frame.id || frame.data ? frame : null;
}
