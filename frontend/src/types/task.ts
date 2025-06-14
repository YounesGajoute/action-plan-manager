export interface Task {
  id: string;
  po_number?: string;          // Optional - Excel sometimes has empty PO
  date_created: string;        // Maps to Excel "Date"
  category?: string;           // Maps to Excel "Catégorie"
  action_description: string;  // Maps to Excel "Action "
  customer: string;            // Maps to Excel "Customer"
  requester: string;           // Maps to Excel "Requester"
  responsible: string;         // Maps to Excel "Techmac Resp"
  deadline?: string;           // Maps to Excel "Dead line "
  status: string;              // Maps to Excel "Status"
  notes?: string;              // Maps to Excel "Note"
  priority?: TaskPriority;     // Not in Excel - system generated
  
  // Excel category flags (additional columns)
  installation_flag?: boolean; // Maps to Excel "Installation/F"
  reparation_flag?: boolean;   // Maps to Excel "Réparation"
  developpement_flag?: boolean; // Maps to Excel "Développement"
  livraison_flag?: boolean;    // Maps to Excel "Livraison "
  
  // System fields
  created_at: string;
  updated_at: string;
}

export type TaskStatus = 
  | 'En Attente' 
  | 'En Cours' 
  | 'Terminé' 
  | 'Annulé' 
  | 'En Pause';

export type TaskPriority = 
  | 'Faible' 
  | 'Moyen' 
  | 'Élevé' 
  | 'Urgent';

export interface TaskCounts {
  total: number;
  pending: number;
  inProgress: number;
  completed: number;
  overdue: number;
  byCategory: Record<string, number>;
  byResponsible: Record<string, number>;
  byStatus: Record<TaskStatus, number>;
}