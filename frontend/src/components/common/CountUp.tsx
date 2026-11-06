import { useCallback, useEffect, useState } from "react";

interface CountUpProps {
  value?: number;
  end?: number;
  decimals?: number;
  duration?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
}

export function CountUp({
  value,
  end,
  decimals,
  duration = 400,
  className,
  prefix = "",
  suffix = "",
}: CountUpProps) {
  const target = value ?? end ?? 0;
  const isTest = typeof process !== "undefined" && process.env?.NODE_ENV === "test";
  const formatVal = useCallback(
    (v: number | undefined) => {
      const num = typeof v === "number" && !isNaN(v) ? v : 0;
      return decimals !== undefined ? num.toFixed(decimals) : Math.round(num).toLocaleString();
    },
    [decimals]
  );

  const [displayValue, setDisplayValue] = useState(() => (isTest ? formatVal(target) : formatVal(0)));

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
        : false;

    if (isTest || prefersReducedMotion || duration <= 0 || target <= 0) {
      setDisplayValue(formatVal(target));
      return;
    }

    let startTimestamp: number | null = null;
    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease-out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = easeProgress * target;
      setDisplayValue(formatVal(current));

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        setDisplayValue(formatVal(target));
      }
    };

    animationFrameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationFrameId);
  }, [target, duration, formatVal, isTest]);

  return (
    <span className={className}>
      {prefix}
      {displayValue}
      {suffix}
    </span>
  );
}
