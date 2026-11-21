import java.util.*;
public class Check {
 static List<String> collect(Hashtable<String,Integer> t) { return Collections.list(t.keys()); }
 static void check(boolean b) { if (!b) throw new AssertionError(); }
 public static void main(String[] args) {
  Hashtable<String,Integer> t=new Hashtable<>(); check(collect(t).isEmpty());
  t.put("One",1); check(collect(t).equals(List.of("One")));
  t.put("Two",2); List<String> v=collect(t); check(v.equals(List.of("Two","One"))); check(new HashSet<>(v).equals(Set.of("One","Two")));
  Enumeration<String> e=t.keys(); e.nextElement(); e.nextElement(); check(!e.hasMoreElements());
  try { e.nextElement(); throw new AssertionError(); } catch (NoSuchElementException expected) { }
  System.out.println("PASS empty, singleton, two keys, membership, exhaustion; order="+v);
 }
}
