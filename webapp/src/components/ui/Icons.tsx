import {
    Users,
    Calendar,
    TrendingUp,
    AlertCircle,
    Plus,
    Edit2,
    Trash2,
    Save,
    ChevronLeft,
    ChevronRight,
    List,
    X,
    Check,
    AlertTriangle,
    Info
} from 'lucide-react';

export const Icons = {
    Users,
    Calendar,
    TrendingUp,
    AlertCircle, // Used for error/admin
    Plus,
    Edit: Edit2, // Alias for better naming
    Delete: Trash2, // Alias for better naming
    Save,
    ChevronLeft,
    ChevronRight,
    List,
    Close: X,
    Check,
    Warning: AlertTriangle,
    Info
};

export type IconName = keyof typeof Icons;
