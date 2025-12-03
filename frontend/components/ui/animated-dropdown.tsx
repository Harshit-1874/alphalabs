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
import { CheckIcon } from "@radix-ui/react-icons"

const TRANSITION = {
  type: "spring" as const,
  bounce: 0.1,
  duration: 0.25,
}

// ============================================================================
// Context
// ============================================================================

interface DropdownContextType {
  isOpen: boolean
  open: () => void
  close: () => void
  toggle: () => void
  uniqueId: string
  triggerRef: React.RefObject<HTMLButtonElement | null>
}

const DropdownContext = createContext<DropdownContextType | undefined>(undefined)

function useDropdown() {
  const context = useContext(DropdownContext)
  if (!context) {
    throw new Error("useDropdown must be used within an AnimatedDropdown")
  }
  return context
}

// ============================================================================
// Root Component
// ============================================================================

interface AnimatedDropdownProps {
  children: React.ReactNode
  className?: string
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function AnimatedDropdown({ 
  children, 
  className,
  open: controlledOpen,
  onOpenChange,
}: AnimatedDropdownProps) {
  const uniqueId = useId()
  const [internalOpen, setInternalOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen
  
  const setOpen = useCallback((value: boolean) => {
    if (controlledOpen === undefined) {
      setInternalOpen(value)
    }
    onOpenChange?.(value)
  }, [controlledOpen, onOpenChange])

  const open = useCallback(() => setOpen(true), [setOpen])
  const close = useCallback(() => setOpen(false), [setOpen])
  const toggle = useCallback(() => setOpen(!isOpen), [setOpen, isOpen])

  return (
    <DropdownContext.Provider value={{ isOpen, open, close, toggle, uniqueId, triggerRef }}>
      <MotionConfig transition={TRANSITION}>
        <div className={cn("relative inline-block", className)}>
          {children}
        </div>
      </MotionConfig>
    </DropdownContext.Provider>
  )
}

// ============================================================================
// Trigger Component
// ============================================================================

interface AnimatedDropdownTriggerProps {
  children: React.ReactNode
  className?: string
  asChild?: boolean
}

export function AnimatedDropdownTrigger({ 
  children, 
  className,
  asChild,
}: AnimatedDropdownTriggerProps) {
  const { toggle, isOpen, triggerRef } = useDropdown()

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<any>, {
      onClick: (e: React.MouseEvent) => {
        e.preventDefault()
        e.stopPropagation()
        toggle()
        ;(children as any).props?.onClick?.(e)
      },
      "aria-expanded": isOpen,
      "aria-haspopup": true,
      ref: triggerRef,
    })
  }

  return (
    <button
      ref={triggerRef}
      type="button"
      className={cn(
        "inline-flex items-center justify-center",
        className
      )}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        toggle()
      }}
      aria-expanded={isOpen}
      aria-haspopup="true"
    >
      {children}
    </button>
  )
}

// ============================================================================
// Content Component (Portal-based to avoid overflow clipping)
// ============================================================================

interface AnimatedDropdownContentProps {
  children: React.ReactNode
  className?: string
  align?: "start" | "center" | "end"
  side?: "top" | "bottom" | "left" | "right"
  sideOffset?: number
}

export function AnimatedDropdownContent({ 
  children, 
  className,
  align = "end",
  side = "bottom",
  sideOffset = 6,
}: AnimatedDropdownContentProps) {
  const { isOpen, close, triggerRef } = useDropdown()
  const contentRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ top: 0, left: 0 })
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

      const contentWidth = contentRef.current?.offsetWidth || 180
      const contentHeight = contentRef.current?.offsetHeight || 0
      const viewportWidth = window.innerWidth
      const viewportHeight = window.innerHeight

      let top = 0
      let left = 0

      // Calculate vertical position
      if (side === "bottom") {
        top = triggerRect.bottom + sideOffset
        // Flip to top if not enough space below
        if (top + contentHeight > viewportHeight - 10) {
          top = triggerRect.top - contentHeight - sideOffset
        }
      } else if (side === "top") {
        top = triggerRect.top - contentHeight - sideOffset
        // Flip to bottom if not enough space above
        if (top < 10) {
          top = triggerRect.bottom + sideOffset
        }
      }

      // Calculate horizontal position
      if (align === "end") {
        left = triggerRect.right - contentWidth
        // Ensure it doesn't go off left edge
        if (left < 10) {
          left = 10
        }
      } else if (align === "start") {
        left = triggerRect.left
        // Ensure it doesn't go off right edge
        if (left + contentWidth > viewportWidth - 10) {
          left = viewportWidth - contentWidth - 10
        }
      } else {
        // center
        left = triggerRect.left + (triggerRect.width - contentWidth) / 2
        // Keep within viewport
        if (left < 10) left = 10
        if (left + contentWidth > viewportWidth - 10) {
          left = viewportWidth - contentWidth - 10
        }
      }

      setPosition({ top, left })
    }

    updatePosition()
    
    // Recalculate on scroll or resize
    window.addEventListener("scroll", updatePosition, true)
    window.addEventListener("resize", updatePosition)
    
    return () => {
      window.removeEventListener("scroll", updatePosition, true)
      window.removeEventListener("resize", updatePosition)
    }
  }, [isOpen, align, side, sideOffset, triggerRef])

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

  const getAnimationOrigin = () => {
    if (side === "bottom") {
      if (align === "start") return "top left"
      if (align === "end") return "top right"
      return "top center"
    }
    if (side === "top") {
      if (align === "start") return "bottom left"
      if (align === "end") return "bottom right"
      return "bottom center"
    }
    return "top center"
  }

  if (!mounted) return null

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={contentRef}
          initial={{ opacity: 0, scale: 0.95, y: side === "bottom" ? -4 : 4 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: side === "bottom" ? -4 : 4 }}
          transition={TRANSITION}
          className={cn(
            "fixed z-[9999] min-w-[12rem] overflow-hidden rounded-lg border bg-popover p-1.5 text-popover-foreground shadow-lg",
            className
          )}
          style={{
            top: position.top,
            left: position.left,
            transformOrigin: getAnimationOrigin(),
          }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}

// ============================================================================
// Item Component
// ============================================================================

interface AnimatedDropdownItemProps {
  children: React.ReactNode
  className?: string
  onSelect?: () => void
  disabled?: boolean
  inset?: boolean
  destructive?: boolean
}

export function AnimatedDropdownItem({ 
  children, 
  className,
  onSelect,
  disabled = false,
  inset = false,
  destructive = false,
}: AnimatedDropdownItemProps) {
  const { close } = useDropdown()

  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center gap-2 rounded-md px-3 py-2 text-sm outline-none transition-colors",
        "focus:bg-accent focus:text-accent-foreground",
        "hover:bg-accent hover:text-accent-foreground",
        disabled && "pointer-events-none opacity-50",
        inset && "pl-8",
        destructive && "text-destructive focus:text-destructive hover:text-destructive focus:bg-destructive/10 hover:bg-destructive/10",
        className
      )}
      onClick={() => {
        if (!disabled) {
          onSelect?.()
          close()
        }
      }}
    >
      {children}
    </button>
  )
}

// ============================================================================
// Label Component
// ============================================================================

interface AnimatedDropdownLabelProps {
  children: React.ReactNode
  className?: string
  inset?: boolean
}

export function AnimatedDropdownLabel({ 
  children, 
  className,
  inset = false,
}: AnimatedDropdownLabelProps) {
  return (
    <div
      className={cn(
        "px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider",
        inset && "pl-8",
        className
      )}
    >
      {children}
    </div>
  )
}

// ============================================================================
// Separator Component
// ============================================================================

interface AnimatedDropdownSeparatorProps {
  className?: string
}

export function AnimatedDropdownSeparator({ className }: AnimatedDropdownSeparatorProps) {
  return (
    <div className={cn("-mx-1.5 my-1.5 h-px bg-border", className)} />
  )
}

// ============================================================================
// Checkbox Item Component
// ============================================================================

interface AnimatedDropdownCheckboxItemProps {
  children: React.ReactNode
  className?: string
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  disabled?: boolean
}

export function AnimatedDropdownCheckboxItem({ 
  children, 
  className,
  checked = false,
  onCheckedChange,
  disabled = false,
}: AnimatedDropdownCheckboxItemProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-md py-2 pl-8 pr-3 text-sm outline-none transition-colors",
        "focus:bg-accent focus:text-accent-foreground",
        "hover:bg-accent hover:text-accent-foreground",
        disabled && "pointer-events-none opacity-50",
        className
      )}
      onClick={() => {
        if (!disabled) {
          onCheckedChange?.(!checked)
        }
      }}
    >
      <span className="absolute left-2.5 flex h-4 w-4 items-center justify-center">
        <AnimatePresence>
          {checked && (
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
      {children}
    </button>
  )
}

// ============================================================================
// Shortcut Component
// ============================================================================

interface AnimatedDropdownShortcutProps {
  children: React.ReactNode
  className?: string
}

export function AnimatedDropdownShortcut({ 
  children, 
  className,
}: AnimatedDropdownShortcutProps) {
  return (
    <span
      className={cn("ml-auto text-xs tracking-widest opacity-60", className)}
    >
      {children}
    </span>
  )
}

// ============================================================================
// Exports
// ============================================================================

export {
  AnimatedDropdown as DropdownMenu,
  AnimatedDropdownTrigger as DropdownMenuTrigger,
  AnimatedDropdownContent as DropdownMenuContent,
  AnimatedDropdownItem as DropdownMenuItem,
  AnimatedDropdownLabel as DropdownMenuLabel,
  AnimatedDropdownSeparator as DropdownMenuSeparator,
  AnimatedDropdownCheckboxItem as DropdownMenuCheckboxItem,
  AnimatedDropdownShortcut as DropdownMenuShortcut,
}
