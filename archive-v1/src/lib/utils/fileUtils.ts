import { promises as fs } from 'fs';
import path from 'path';

export async function backupFile(filePath: string): Promise<string> {
  const ext = path.extname(filePath);
  const base = path.basename(filePath, ext);
  const dir = path.dirname(filePath);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(dir, `${base}_backup_${timestamp}${ext}`);
  
  await fs.copyFile(filePath, backupPath);
  return backupPath;
}

export async function processAbletonFile(
  inputPath: string, 
  processFunction: (content: string) => string | { code: string, message: string }
): Promise<{ success: boolean; message: string }> {
  try {
    // Create backup
    const backupPath = await backupFile(inputPath);

    // Read file
    const content = await fs.readFile(inputPath, 'utf-8');

    // Process content
    const result = processFunction(content);

    if (typeof result === 'string') {
      // Write modified content
      await fs.writeFile(inputPath, result, 'utf-8');
      return {
        success: true,
        message: `File processed successfully. Backup created at: ${backupPath}`
      };
    } else {
      return {
        success: false,
        message: `Processing failed: ${result.message}`
      };
    }
  } catch (error) {
    return {
      success: false,
      message: `Error processing file: ${error.message}`
    };
  }
} 