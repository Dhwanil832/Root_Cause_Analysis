import { strFromU8, unzipSync } from 'fflate';
import { extractText as extractPdfText } from 'unpdf';

const MAX_EXTRACTED_CHARS = 160_000;

export interface ExtractedDocument {
  text: string;
  status: 'ready' | 'partial' | 'unsupported' | 'failed';
  notes: string;
}

function decodeEntities(value: string) {
  return value
    .replace(/<w:tab\s*\/>/g, '\t')
    .replace(/<w:br\s*\/>/g, '\n')
    .replace(/<a:br\s*\/>/g, '\n')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function xmlText(xml: string) {
  return decodeEntities(xml)
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, '\n')
    .trim();
}

function officeText(bytes: Uint8Array, extension: string) {
  const archive = unzipSync(bytes);
  if (extension === 'docx') {
    const main = archive['word/document.xml'];
    if (!main) throw new Error('DOCX document body was not found.');
    return xmlText(strFromU8(main).replace(/<\/w:p>/g, '\n'));
  }
  if (extension === 'pptx') {
    const slides = Object.entries(archive)
      .filter(([name]) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
      .sort(([a], [b]) => Number(a.match(/\d+/)?.[0]) - Number(b.match(/\d+/)?.[0]));
    return slides.map(([name, data]) => `${name}\n${xmlText(strFromU8(data).replace(/<\/a:p>/g, '\n'))}`).join('\n\n');
  }
  if (extension === 'xlsx') {
    const sharedRaw = archive['xl/sharedStrings.xml'];
    const shared = sharedRaw
      ? [...strFromU8(sharedRaw).matchAll(/<si[^>]*>([\s\S]*?)<\/si>/g)].map((match) => xmlText(match[1]))
      : [];
    const sheets = Object.entries(archive)
      .filter(([name]) => /^xl\/worksheets\/sheet\d+\.xml$/.test(name))
      .sort(([a], [b]) => Number(a.match(/\d+/)?.[0]) - Number(b.match(/\d+/)?.[0]));
    return sheets.map(([name, data]) => {
      const xml = strFromU8(data);
      const rows = [...xml.matchAll(/<row[^>]*>([\s\S]*?)<\/row>/g)].map((row) => {
        const cells = [...row[1].matchAll(/<c([^>]*)>([\s\S]*?)<\/c>/g)].map((cell) => {
          const value = cell[2].match(/<v>([\s\S]*?)<\/v>/)?.[1] || '';
          return /t="s"/.test(cell[1]) ? shared[Number(value)] || value : xmlText(value);
        });
        return cells.join('\t');
      });
      return `${name}\n${rows.join('\n')}`;
    }).join('\n\n');
  }
  throw new Error('Unsupported Office format.');
}

export async function extractDocument(bytes: ArrayBuffer, fileName: string, contentType: string): Promise<ExtractedDocument> {
  const extension = fileName.split('.').pop()?.toLowerCase() || '';
  try {
    let text = '';
    let notes = '';
    if (['txt', 'md', 'csv', 'json', 'log', 'xml'].includes(extension) || contentType.startsWith('text/')) {
      text = new TextDecoder().decode(bytes);
    } else if (['docx', 'pptx', 'xlsx'].includes(extension)) {
      text = officeText(new Uint8Array(bytes), extension);
    } else if (extension === 'pdf' || contentType === 'application/pdf') {
      const result = await extractPdfText(new Uint8Array(bytes), { mergePages: true });
      text = result.text;
      notes = `Extracted text from ${result.totalPages} PDF pages.`;
    } else if (contentType.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif', 'tif', 'tiff'].includes(extension)) {
      return {
        text: '',
        status: 'partial',
        notes: 'Original image preserved. Text extraction is unavailable; route visual interpretation to a compatible vision model or a human reviewer.',
      };
    } else {
      return { text: '', status: 'unsupported', notes: 'Original file preserved; this format has no configured text extractor.' };
    }
    const normalized = text.replace(/\u0000/g, '').trim();
    if (!normalized) return { text: '', status: 'partial', notes: notes || 'No machine-readable text was found.' };
    const truncated = normalized.length > MAX_EXTRACTED_CHARS;
    return {
      text: normalized.slice(0, MAX_EXTRACTED_CHARS),
      status: truncated ? 'partial' : 'ready',
      notes: [notes, truncated ? `Text limited to ${MAX_EXTRACTED_CHARS.toLocaleString()} characters for investigation context.` : ''].filter(Boolean).join(' '),
    };
  } catch (error) {
    return { text: '', status: 'failed', notes: error instanceof Error ? error.message : 'Document extraction failed.' };
  }
}

export async function sha256(bytes: ArrayBuffer) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, '0')).join('');
}
