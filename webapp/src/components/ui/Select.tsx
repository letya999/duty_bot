import React, { SelectHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    error?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
    ({ className, label, error, children, ...props }, ref) => {
        return (
            <div className={cn("w-full", className?.includes("w-") ? "" : "w-full")}>
                {label && (
                    <label className="block text-sm font-medium text-text mb-1">
                        {label}
                    </label>
                )}
                <select
                    className={cn(
                        "w-full px-3 py-2 border border-border rounded-md bg-background-secondary text-text focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50",
                        error && "border-red-500 focus:ring-red-500",
                        className
                    )}
                    ref={ref}
                    {...props}
                >
                    {children}
                </select>
                {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
            </div>
        );
    }
);
Select.displayName = "Select";
