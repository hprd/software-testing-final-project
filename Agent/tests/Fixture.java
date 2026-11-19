import java.util.*;
import java.util.stream.*;
class Fixture {
 static void assertEquals(Object a,Object b) { }
 void test(Hashtable<String,Integer> table) {
  assertEquals(Arrays.asList("a", "b"), Collections.list(table.keys()));
  assertEquals(Arrays.asList("a", "b"), Collections.list(table.keys()).stream().sorted().collect(Collectors.toList()));
  Collections.list(table.keys()).contains("a");
  MissingType.missing();
 }
}
