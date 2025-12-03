"use client"

import React, {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  useCallback,
} from "react"
import { createPortal } from "react-dom"
import { AnimatePresence, motion, MotionConfig } from "motion/react"
import { cn } from "@/lib/utils"
import { CheckIcon, ChevronDownIcon } from "@radix-ui/react-icons"

const TRANSITION = {
  type: "spring" as const,
  bounce: 0.1,
  duration: 0.25,
}

// Helper to extract text from React children
function extractTextFromChildren(children: React.ReactNode): string {
  if (typeof children === "string") return children
  if (typeof children === "number") return String(children)
  if (!children) return ""
  
  if (Array.isArray(children)) {
    return children.map(extractTextFromChildren).join("")
  }
  
  if (React.isValidElement(children)) {
    const props = children.props as { children?: React.ReactNode }
    return extractTextFromChildren(props.children)
  }
  
  return ""
}

// ============================================================================
// Context
// ============================================================================

interface SelectContextType {
  isOpen: boolean
  open: () => void
  close: () => void
  toggle: () => void
  uniqueId: string
  value: string
  onValueChange: (value: string, displayText: string) => void
  triggerRef: React.RefObject<HTMLButtonElement | null>
  displayValue: string
  setDisplayText: (text: string) => void
}

const SelectContext = createContext<SelectContextType | undefined>(undefined)

function useSelect() {
  const context = useContext(SelectContext)
  if (!context) {
    throw new Error("useSelect must be used within an AnimatedSelect")
  }
  return context
}

// ============================================================================
// Root Component
// ============================================================================

interface AnimatedSelectProps {
  children: React.ReactNode
  className?: string
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  /** Optional: Provide initial display value to avoid waiting for items to mount */
  defaultDisplayValue?: string
}

export function AnimatedSelect({ 
  children, 
  className,
  value: controlledValue,
  defaultValue = "",
  defaultDisplayValue,
  onValueChange,
}: AnimatedSelectProps) {
  const uniqueId = useId()
  const [isOpen, setIsOpen] = useState(false)
  const [internalValue, setInternalValue] = useState(defaultValue)
  const [displayValue, setDisplayValue] = useState(defaultDisplayValue || "")
  const triggerRef = useRef<HTMLButtonElement>(null)
  const childrenRef = useRef(children)

  const value = controlledValue !== undefined ? controlledValue : internalValue
  
  // Update children ref when children change
  useEffect(() => {
    childrenRef.current = children
  }, [children])
  
  // Try to extract display value from children when value changes
  useEffect(() => {
    if (value && !displayValue) {
      // Try to find the matching item in children and extract its text
      const extractDisplayValueFromChildren = (children: React.ReactNode): string | null => {
        let result: string | null = null;
        
        React.Children.forEach(children, (child) => {
          if (result) return; // Already found
          
          if (React.isValidElement(child)) {
            const props = child.props as any;
            
            // Check if this is a SelectContent or similar wrapper
            if (props.children) {
              const found = extractDisplayValueFromChildren(props.children);
              if (found) result = found;
            }
            
            // Check if this is the matching SelectItem
            if (props.value === value) {
              // Try textValue first, then extract from children
              result = props.textValue || extractTextFromChildren(props.children) || value;
            }
          }
        });
        
        return result;
      };
      
      const extracted = extractDisplayValueFromChildren(childrenRef.current);
      if (extracted) {
        setDisplayValue(extracted);
      }
    }
  }, [value, displayValue])
  
  const handleValueChange = useCallback((newValue: string, displayText: string) => {
    if (controlledValue === undefined) {
      setInternalValue(newValue)
    }
    setDisplayValue(displayText)
    onValueChange?.(newValue)
    setIsOpen(false)
  }, [controlledValue, onValueChange])

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen(prev => !prev), [])

  const setDisplayText = useCallback((text: string) => {
    setDisplayValue(text)
  }, [displayValue])


  return (
    <SelectContext.Provider value={{ 
      isOpen, 
      open, 
      close, 
      toggle, 
      uniqueId, 
      value, 
      onValueChange: handleValueChange,
      triggerRef,
      displayValue,
      setDisplayText,
    }}>
      <MotionConfig transition={TRANSITION}>
        <div className={cn("relative inline-block w-full", className)}>
          {children}
        </div>
      </MotionConfig>
    </SelectContext.Provider>
  )
}

// ============================================================================
// Trigger Component
// ============================================================================

interface AnimatedSelectTriggerProps {
  children: React.ReactNode
  className?: string
}

export function AnimatedSelectTrigger({ 
  children, 
  className,
}: AnimatedSelectTriggerProps) {
  const { toggle, isOpen, triggerRef, displayValue } = useSelect()

  return (
    <button
      ref={triggerRef}
      type="button"
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background transition-all",
        "data-[placeholder]:text-muted-foreground",
        "focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "[&>span]:overflow-hidden [&>span]:text-left",
        "hover:border-border/80",
        className
      )}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        toggle()
      }}
      aria-expanded={isOpen}
      aria-haspopup="listbox"
      data-placeholder={!displayValue ? "" : undefined}
    >
      <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
        {children}
      </span>
      <motion.div
        animate={{ rotate: isOpen ? 180 : 0 }}
        transition={{ duration: 0.2 }}
        className="shrink-0 ml-2"
      >
        <ChevronDownIcon className="h-4 w-4 opacity-50" />
      </motion.div>
    </button>
  )
}

// ============================================================================
// Value Component
// ============================================================================

interface AnimatedSelectValueProps {
  placeholder?: string
  className?: string
}

export function AnimatedSelectValue({ 
  placeholder = "Select...",
  className,
}: AnimatedSelectValueProps) {
  const { displayValue } = useSelect()

  return (
    <span className={cn(
      "block truncate",
      !displayValue && "text-muted-foreground",
      className
    )}>
      {displayValue || placeholder}
    </span>
  )
}

// ============================================================================
// Content Component (Portal-based to avoid overflow clipping)
// ============================================================================

interface AnimatedSelectContentProps {
  children: React.ReactNode
  className?: string
  position?: "item-aligned" | "popper"
}

export function AnimatedSelectContent({ 
  children, 
  className,
}: AnimatedSelectContentProps) {
  const { isOpen, close, triggerRef } = useSelect()
  const contentRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 })
  const [mounted, setMounted] = useState(false)

  // Handle SSR
  useEffect(() => {
    setMounted(true)
  }, [])

  // Calculate position based on trigger element
  useEffect(() => {
    if (!isOpen || !triggerRef.current) return

    const updatePosition = () => {
      const triggerRect = triggerRef.current?.getBoundingClientRect()
      if (!triggerRect) return

      const contentHeight = contentRef.current?.offsetHeight || 300
      const viewportHeight = window.innerHeight
      const sideOffset = 6

      let top = triggerRect.bottom + sideOffset
      
      // Flip to top if not enough space below
      if (top + contentHeight > viewportHeight - 10) {
        top = triggerRect.top - contentHeight - sideOffset
        // If still not enough space, position at top of viewport with scroll
        if (top < 10) {
          top = 10
        }
      }

      setPosition({
        top,
        left: triggerRect.left,
        width: triggerRect.width,
      })
    }

    updatePosition()
    
    window.addEventListener("scroll", updatePosition, true)
    window.addEventListener("resize", updatePosition)
    
    return () => {
      window.removeEventListener("scroll", updatePosition, true)
      window.removeEventListener("resize", updatePosition)
    }
  }, [isOpen, triggerRef])

  // Click outside handler
  useEffect(() => {
    if (!isOpen) return

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (
        contentRef.current && 
        !contentRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        close()
      }
    }

    const timeoutId = setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside)
    }, 0)

    return () => {
      clearTimeout(timeoutId)
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [isOpen, close, triggerRef])

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, close])

  if (!mounted) return null

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={contentRef}
          role="listbox"
          initial={{ opacity: 0, y: -8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.96 }}
          transition={TRANSITION}
          className={cn(
            "fixed z-[9999] overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-lg",
            className
          )}
          style={{
            top: position.top,
            left: position.left,
            width: position.width,
            minWidth: "12rem",
            transformOrigin: "top center",
          }}
        >
          <div className="p-1.5 max-h-[300px] overflow-y-auto">
            {children}
          </div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}

// ============================================================================
// Item Component
// ============================================================================

interface AnimatedSelectItemProps {
  children: React.ReactNode
  value: string
  className?: string
  disabled?: boolean
  /** Explicit text to display when selected. If not provided, text is extracted from children. */
  textValue?: string
}

export function AnimatedSelectItem({ 
  children, 
  value: itemValue,
  className,
  disabled = false,
  textValue,
}: AnimatedSelectItemProps) {
  const { value, onValueChange, displayValue, setDisplayText } = useSelect()
  const isSelected = value === itemValue
  const [hasSetInitial, setHasSetInitial] = useState(false)
  
  // Get the display text - either from textValue prop or extracted from children
  const displayText = textValue || extractTextFromChildren(children) || itemValue

  // Sync display value on mount if this item is already selected (for controlled components)
  // Only run once to avoid infinite loops
  useEffect(() => {
    if (isSelected && displayText && !hasSetInitial) {
      setDisplayText(displayText)
      setHasSetInitial(true)
    }
  }, [isSelected, displayText, setDisplayText, hasSetInitial])

  return (
    <button
      type="button"
      role="option"
      aria-selected={isSelected}
      disabled={disabled}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-md py-2 pl-3 pr-9 text-sm outline-none transition-colors",
        "focus:bg-accent focus:text-accent-foreground",
        "hover:bg-accent hover:text-accent-foreground",
        isSelected && "bg-accent/50",
        disabled && "pointer-events-none opacity-50",
        className
      )}
      onClick={() => {
        if (!disabled) {
          onValueChange(itemValue, displayText)
        }
      }}
    >
      <span className="flex-1 text-left">{children}</span>
      <span className="absolute right-3 flex h-4 w-4 items-center justify-center">
        <AnimatePresence>
          {isSelected && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.15 }}
            >
              <CheckIcon className="h-4 w-4" />
            </motion.div>
          )}
        </AnimatePresence>
      </span>
    </button>
  )
}

// ============================================================================
// Group Component
// ============================================================================

interface AnimatedSelectGroupProps {
  children: React.ReactNode
  className?: string
}

export function AnimatedSelectGroup({ 
  children, 
  className,
}: AnimatedSelectGroupProps) {
  return (
    <div className={cn("", className)} role="group">
      {children}
    </div>
  )
}

// ============================================================================
// Label Component
// ============================================================================

interface AnimatedSelectLabelProps {
  children: React.ReactNode
  className?: string
}

export function AnimatedSelectLabel({ 
  children, 
  className,
}: AnimatedSelectLabelProps) {
  return (
    <div
      className={cn("px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider", className)}
    >
      {children}
    </div>
  )
}

// ============================================================================
// Separator Component
// ============================================================================

interface AnimatedSelectSeparatorProps {
  className?: string
}

export function AnimatedSelectSeparator({ className }: AnimatedSelectSeparatorProps) {
  return (
    <div className={cn("-mx-1.5 my-1.5 h-px bg-border", className)} />
  )
}

// ============================================================================
// Exports (with aliases for drop-in replacement)
// ============================================================================

export {
  AnimatedSelect as Select,
  AnimatedSelectTrigger as SelectTrigger,
  AnimatedSelectValue as SelectValue,
  AnimatedSelectContent as SelectContent,
  AnimatedSelectItem as SelectItem,
  AnimatedSelectGroup as SelectGroup,
  AnimatedSelectLabel as SelectLabel,
  AnimatedSelectSeparator as SelectSeparator,
}
