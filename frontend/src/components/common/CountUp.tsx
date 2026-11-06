import { useCallback, useEffect, useState } from "react";

interface CountUpProps {
  value: number;
  decimals?: number;
  duration?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
}

export function CountUp({
  value,
  decimals,
  duration = 400,
  className,
  prefix = "",
  suffix = "",
}: CountUpProps) {
  const isTest = typeof process !== "undefined" && process.env?.NODE_ENV === "test";
  const formatVal = useCallback(
    (v: number) => (decimals !== undefined ? v.toFixed(decimals) : Math.round(v).toLocaleString()),
    [decimals]
  );

  const [displayValue, setDisplayValue] = useState(() => (isTest ? formatVal(value) : formatVal(0)));

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
        : false;

    if (isTest || prefersReducedMotion || duration <= 0 || value <= 0) {
      setDisplayValue(formatVal(value));
      return;
    }

    let startTimestamp: number | null = null;
    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease-out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = easeProgress * value;
      setDisplayValue(formatVal(current));

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        setDisplayValue(formatVal(value));
      }
    };

    animationFrameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationFrameId);
  }, [value, duration, formatVal, isTest]);

  return (
    <span className={className}>
      {prefix}
      {displayValue}
      {suffix}
    </span>
  );
}
