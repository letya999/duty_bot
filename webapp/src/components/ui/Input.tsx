import React, { InputHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className, label, error, type = "text", ...props }, ref) => {
        return (
            <div className={cn("w-full", className?.includes("w-") ? "" : "w-full")}>
                {label && (
                    <label className="block text-sm font-medium text-text mb-1">
                        {label}
                    </label>
                )}
                <input
                    type={type}
                    className={cn(
                        "w-full px-3 py-2 border border-border rounded-md bg-background-secondary text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50",
                        error && "border-red-500",
                        className
                    )}
                    ref={ref}
                    {...props}
                />
                {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
            </div>
        );
    }
);
Input.displayName = "Input";
