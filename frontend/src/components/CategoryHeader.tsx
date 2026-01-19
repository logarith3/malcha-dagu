import { motion } from 'framer-motion';

interface Props {
    taxonomy: {
        title: string;
        type: string;
        brand: string;
        breadcrumbs: string[];
        description: string;
        logo_url?: string;
    };
}

export default function CategoryHeader({ taxonomy }: Props) {
    return (
        <div className="mb-6">
            {/* Breadcrumbs */}
            <div className="flex items-center gap-2 text-xs font-medium text-stone-400 mb-2 overflow-x-auto whitespace-nowrap scrollbar-hide">
                {taxonomy.breadcrumbs.map((crumb, index) => (
                    <div key={index} className="flex items-center gap-2">
                        {index > 0 && <span className="text-stone-300">›</span>}
                        <span className={index === taxonomy.breadcrumbs.length - 1 ? "text-matcha-600 font-bold" : "hover:text-stone-600 cursor-pointer transition-colors"}>
                            {crumb}
                        </span>
                    </div>
                ))}
            </div>

            {/* Title & Description */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                <div className="flex items-center gap-4 mb-2">
                    {/* Logo (if available) */}
                    {taxonomy.logo_url && (
                        <img
                            src={taxonomy.logo_url}
                            alt={taxonomy.brand}
                            className="w-12 h-12 object-contain p-1 bg-white rounded-lg border border-stone-100"
                        />
                    )}

                    <div className="flex items-baseline gap-3">
                        <h1 className="text-3xl sm:text-4xl font-black text-stone-800 tracking-tight">
                            {taxonomy.title}
                        </h1>
                        <span className="px-2.5 py-0.5 rounded-full bg-stone-100 text-stone-500 text-[10px] font-bold uppercase tracking-wide border border-stone-200">
                            {taxonomy.type}
                        </span>
                    </div>
                </div>

                <p className="text-stone-500 font-medium leading-relaxed max-w-2xl">
                    {taxonomy.description}
                </p>
            </motion.div>

            {/* Divider */}
            <div className="h-px w-full bg-gradient-to-r from-stone-200 via-stone-100 to-transparent my-6" />
        </div>
    );
}
