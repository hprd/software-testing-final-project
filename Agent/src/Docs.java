import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.tools.*;
import java.nio.file.*;
import java.util.*;

public class Docs {
 static String q(Object x) {if(x==null)return "null";StringBuilder b=new StringBuilder("\"");for(char c:x.toString().toCharArray()){switch(c){case '"':b.append("\\\"");break;case '\\':b.append("\\\\");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default:if(c<32)b.append(String.format("\\u%04x",(int)c));else b.append(c);}}return b.append('"').toString();}
 public static void main(String[] args)throws Exception {
  JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
  for(String line:Files.readAllLines(Path.of(args[0]))) {
   String[] a=line.split("\t",2); String owner=a[0];
   try(StandardJavaFileManager fm=compiler.getStandardFileManager(null,null,null)) {
    var task=(JavacTask)compiler.getTask(null,fm,d->{},List.of("-proc:none"),null,fm.getJavaFileObjects(a[1]));
    var docs=DocTrees.instance(task);
    for(CompilationUnitTree unit:task.parse()) new TreePathScanner<Void,Void>() {
     final Deque<String> names=new ArrayDeque<>();
     public Void visitClass(ClassTree n,Void unused) {
      names.addLast(n.getSimpleName().toString());
      String pkg=unit.getPackageName()==null?"":unit.getPackageName()+".";
      String actual=pkg+String.join(".",names);
      if(owner.equals(actual)) {
       var path=getCurrentPath(); var doc=docs.getDocCommentTree(path);
       String decl=n.getKind()+" "+n.getSimpleName()+" extends "+n.getExtendsClause()+" implements "+n.getImplementsClause();
       System.out.println("{\"owner\":"+q(owner)+",\"kind\":\"class\",\"declaration\":"+q(decl)+",\"doc\":"+q(doc)+"}");
       for(Tree member:n.getMembers()) if(member instanceof MethodTree) {
        MethodTree m=(MethodTree)member; var md=docs.getDocCommentTree(new TreePath(path,m));
        String method=m.getName().contentEquals("<init>")?n.getSimpleName().toString():m.getName().toString();
        String declaration=m.getReturnType()+" "+method+"("+m.getParameters()+")";
        System.out.println("{\"owner\":"+q(owner)+",\"kind\":\"method\",\"name\":"+q(method)+",\"declaration\":"+q(declaration)+",\"doc\":"+q(md)+"}");
       }
      }
      super.visitClass(n,unused);names.removeLast();return null;
     }
    }.scan(unit,null);
   } catch(Exception ex) {System.err.println(owner+": "+ex);}
  }
 }
}
