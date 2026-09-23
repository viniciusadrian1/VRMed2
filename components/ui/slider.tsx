"use client";

import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";
import { faixasDOMXR } from "@/lib/painel-dom-xr";

function Slider({
  className,
  ...props
}: React.ComponentProps<typeof SliderPrimitive.Root>) {
  const values = Array.isArray(props.value)
    ? props.value
    : Array.isArray(props.defaultValue)
      ? props.defaultValue
      : [0];

  return (
    <SliderPrimitive.Root
      ref={(elemento) => {
        if (elemento) faixasDOMXR.set(elemento, {
          min: props.min ?? 0, max: props.max ?? 100, step: props.step ?? 1, disabled: props.disabled,
          mudar: (valor) => props.onValueChange?.([valor]),
        });
      }}
      data-slot="slider"
      className={cn(
        "relative flex w-full touch-none select-none items-center data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-secondary">
        <SliderPrimitive.Range className="absolute h-full bg-primary" />
      </SliderPrimitive.Track>
      {values.map((_, i) => (
        <SliderPrimitive.Thumb
          key={i}
          // O papel "slider" fica no polegar, não na raiz: sem repassar o
          // rótulo, leitores de tela anunciavam só "controle deslizante".
          aria-label={props["aria-label"]}
          className="block size-4 rounded-full border-2 border-primary bg-background shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:pointer-events-none"
        />
      ))}
    </SliderPrimitive.Root>
  );
}

export { Slider };
