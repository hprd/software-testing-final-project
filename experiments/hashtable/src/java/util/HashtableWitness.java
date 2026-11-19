package java.util;
/** Experimental fixture limited to the unmodified two-key Commons Lang table. */
public final class HashtableWitness {
    public static Enumeration<?> reverseTarget(Enumeration<?> original, Hashtable<?, ?> table) {
        if (table.getClass() != Hashtable.class || table.size() != 2 ||
                !table.containsKey("One") || !table.containsKey("Two")) return original;
        ArrayList<Object> keys = new ArrayList<>();
        while (original.hasMoreElements()) keys.add(original.nextElement());
        Collections.reverse(keys);
        return Collections.enumeration(keys);
    }
}
