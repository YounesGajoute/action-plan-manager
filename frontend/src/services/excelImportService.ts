import * as XLSX from 'xlsx';
import { Task, TaskStatus } from '../types/task';
import { v4 as uuidv4 } from 'uuid';

interface ExcelRow {
  'Date': any;
  'PO': string;
  'Catégorie': string;
  'Action ': string;       // Note: trailing space in Excel
  'Colonne1': string;      // Additional column found in Excel
  'Customer': string;
  'Requester': string;
  'Techmac Resp': string;
  'Dead line ': any;       // Note: trailing space in Excel
  'Status': string;
  'Note': string;
  'Installation/F': any;
  'Réparation': any;
  'Développement': any;
  'Livraison ': any;       // Note: trailing space in Excel
}

export class ExcelImportService {
  static async importTasks(file: File): Promise<Task[]> {
    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, {
        type: 'array',
        cellDates: true,
        cellNF: false,
        cellText: false
      });

      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const rawData: ExcelRow[] = XLSX.utils.sheet_to_json(worksheet, {
        header: 1,
        defval: '',
        blankrows: false
      });

      // Skip header row and filter out empty rows
      const dataRows = rawData
        .slice(1) // Skip header
        .filter(row => row['Action '] && row['Action '].toString().trim());

      console.log(`Processing ${dataRows.length} rows from Excel`);
      
      return dataRows.map((row, index) => this.mapExcelRowToTask(row, index));
    } catch (error) {
      console.error('Excel import error:', error);
      throw new Error('Failed to import Excel file. Please check the file format.');
    }
  }

  private static mapExcelRowToTask(row: ExcelRow, index: number): Task {
    const task: Task = {
      id: uuidv4(),
      po_number: this.cleanString(row['PO']) || undefined,
      date_created: this.parseExcelDate(row['Date']),
      category: this.mapCategory(row['Catégorie']) || this.inferCategoryFromFlags(row),
      action_description: this.cleanString(row['Action ']) || '',
      customer: this.cleanString(row['Customer']) || '',
      requester: this.cleanString(row['Requester']) || '',
      responsible: this.cleanString(row['Techmac Resp']) || '',
      deadline: this.parseExcelDate(row['Dead line ']) || undefined,
      status: this.normalizeStatus(row['Status']),
      notes: this.cleanString(row['Note']) || undefined,
      
      // Category flags from Excel additional columns
      installation_flag: this.isFlagSet(row['Installation/F']),
      reparation_flag: this.isFlagSet(row['Réparation']),
      developpement_flag: this.isFlagSet(row['Développement']),
      livraison_flag: this.isFlagSet(row['Livraison ']),
      
      // System fields
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Handle Colonne1 if it contains useful data
    const colonne1Value = this.cleanString(row['Colonne1']);
    if (colonne1Value && !task.category) {
      task.category = this.mapCategory(colonne1Value);
    }

    return task;
  }

  private static inferCategoryFromFlags(row: ExcelRow): string | undefined {
    if (this.isFlagSet(row['Installation/F'])) return 'Installation';
    if (this.isFlagSet(row['Réparation'])) return 'Réparation';
    if (this.isFlagSet(row['Développement'])) return 'Développement';
    if (this.isFlagSet(row['Livraison '])) return 'Livraison';
    return undefined;
  }

  private static parseExcelDate(dateValue: any): string {
    if (!dateValue) return new Date().toISOString();
    
    try {
      // Handle Excel serial number dates
      if (typeof dateValue === 'number') {
        const date = new Date((dateValue - 25569) * 86400 * 1000);
        return date.toISOString();
      }
      
      // Handle string dates in DD/MM/YY or DD/MM/YYYY format
      if (typeof dateValue === 'string') {
        const dateStr = dateValue.trim();
        
        // DD/MM/YY or DD/MM/YYYY format (French format)
        if (dateStr.match(/^\d{1,2}\/\d{1,2}\/\d{2,4}$/)) {
          const [day, month, year] = dateStr.split('/');
          let fullYear = year;
          
          // Convert 2-digit year to 4-digit
          if (year.length === 2) {
            const currentYear = new Date().getFullYear();
            const century = Math.floor(currentYear / 100) * 100;
            const yearNum = parseInt(year);
            
            // Assume years 00-30 are 2000s, 31-99 are 1900s
            if (yearNum <= 30) {
              fullYear = String(century + yearNum);
            } else {
              fullYear = String(century - 100 + yearNum);
            }
          }
          
          const isoDate = `${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
          const parsedDate = new Date(isoDate);
          
          if (!isNaN(parsedDate.getTime())) {
            return parsedDate.toISOString();
          }
        }
        
        // Try parsing as ISO string
        const parsedDate = new Date(dateStr);
        if (!isNaN(parsedDate.getTime())) {
          return parsedDate.toISOString();
        }
      }
      
      // Handle Date objects
      if (dateValue instanceof Date) {
        return dateValue.toISOString();
      }
      
      // Fallback to current date
      console.warn('Could not parse date:', dateValue, 'using current date');
      return new Date().toISOString();
    } catch (error) {
      console.warn('Date parsing error:', error, 'for value:', dateValue);
      return new Date().toISOString();
    }
  }

  private static normalizeStatus(status: string): TaskStatus {
    if (!status) return 'En Attente';
    
    const statusStr = status.toString().toLowerCase().trim();
    
    const statusMap: Record<string, TaskStatus> = {
      'done': 'Terminé',
      'completed': 'Terminé',
      'finished': 'Terminé',
      'terminé': 'Terminé',
      'fini': 'Terminé',
      'complete': 'Terminé',
      
      'pending': 'En Attente',
      'waiting': 'En Attente',
      'en attente': 'En Attente',
      'attente': 'En Attente',
      'wait': 'En Attente',
      
      'in-progress': 'En Cours',
      'in progress': 'En Cours',
      'progress': 'En Cours',
      'en cours': 'En Cours',
      'cours': 'En Cours',
      'working': 'En Cours',
      
      'cancelled': 'Annulé',
      'canceled': 'Annulé',
      'annulé': 'Annulé',
      'annule': 'Annulé',
      'cancel': 'Annulé',
      
      'on-hold': 'En Pause',
      'on hold': 'En Pause',
      'hold': 'En Pause',
      'pause': 'En Pause',
      'en pause': 'En Pause',
      'paused': 'En Pause',
    };
    
    return statusMap[statusStr] || 'En Attente';
  }

  private static mapCategory(category: string): string | undefined {
    if (!category) return undefined;
    
    const categoryStr = category.toString().toLowerCase().trim();
    
    const categoryMap: Record<string, string> = {
      'installation': 'Installation',
      'install': 'Installation',
      'installing': 'Installation',
      'setup': 'Installation',
      
      'reparation': 'Réparation',
      'réparation': 'Réparation',
      'repair': 'Réparation',
      'fix': 'Réparation',
      'fixing': 'Réparation',
      'maintenance': 'Réparation',
      
      'developpement': 'Développement',
      'développement': 'Développement',
      'development': 'Développement',
      'dev': 'Développement',
      'programming': 'Développement',
      'coding': 'Développement',
      
      'livraison': 'Livraison',
      'delivery': 'Livraison',
      'shipping': 'Livraison',
      'transport': 'Livraison',
      'expedition': 'Livraison',
      
      'commercial': 'Commercial',
      'sales': 'Commercial',
      'vente': 'Commercial',
      'marketing': 'Commercial',
      'business': 'Commercial',
    };
    
    return categoryMap[categoryStr] || this.capitalizeFirstLetter(category);
  }

  private static capitalizeFirstLetter(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  private static isFlagSet(value: any): boolean {
    if (!value) return false;
    
    const strValue = value.toString().toLowerCase().trim();
    return strValue === 'true' || 
           strValue === '1' || 
           strValue === 'yes' || 
           strValue === 'oui' || 
           strValue === 'x' ||
           strValue === '✓' ||
           strValue === 'checked' ||
           (strValue !== '' && strValue !== '0' && strValue !== 'false' && strValue !== 'no' && strValue !== 'non');
  }

  private static cleanString(value: any): string {
    if (value === null || value === undefined) return '';
    return value.toString().trim();
  }

  static validateExcelFile(file: File): { valid: boolean; error?: string } {
    // Check file type
    const validTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'application/excel',
      'application/x-excel',
      'application/x-msexcel'
    ];
    
    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
      return {
        valid: false,
        error: 'Type de fichier invalide. Veuillez sélectionner un fichier Excel (.xlsx ou .xls)'
      };
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      return {
        valid: false,
        error: 'Fichier trop volumineux. Taille maximale: 10MB'
      };
    }

    // Check if file is not empty
    if (file.size === 0) {
      return {
        valid: false,
        error: 'Le fichier est vide'
      };
    }

    return { valid: true };
  }

  static async validateExcelStructure(file: File): Promise<{ valid: boolean; error?: string; headers?: string[] }> {
    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array' });
      
      if (workbook.SheetNames.length === 0) {
        return { valid: false, error: 'Le fichier Excel ne contient aucune feuille' };
      }

      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1');
      
      if (range.e.r < 1) {
        return { valid: false, error: 'Le fichier Excel ne contient pas suffisamment de lignes' };
      }

      // Extract headers
      const headers: string[] = [];
      for (let col = range.s.c; col <= range.e.c; col++) {
        const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
        const cell = worksheet[cellAddress];
        if (cell && cell.v) {
          headers.push(cell.v.toString());
        }
      }

      // Check for required headers
      const requiredHeaders = ['Action ', 'Customer', 'Requester', 'Techmac Resp'];
      const missingHeaders = requiredHeaders.filter(header => 
        !headers.some(h => h.trim().toLowerCase().includes(header.trim().toLowerCase()))
      );

      if (missingHeaders.length > 0) {
        return {
          valid: false,
          error: `Colonnes manquantes dans le fichier Excel: ${missingHeaders.join(', ')}`,
          headers
        };
      }

      return { valid: true, headers };
    } catch (error) {
      return {
        valid: false,
        error: 'Impossible de lire le fichier Excel. Vérifiez que le fichier n\'est pas corrompu.'
      };
    }
  }
}