import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.lang.model.element.*;
import javax.tools.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class Inventory {
 static String q(Object x) { if (x==null) return "null"; String s=x.toString(); StringBuilder b=new StringBuilder("\""); for(char c:s.toCharArray()) {switch(c){case '"':b.append("\\\"");break;case '\\':b.append("\\\\");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default: if(c<32)b.append(String.format("\\u%04x",(int)c)); else b.append(c);}}return b.append('"').toString(); }
 public static void main(String[] args) throws Exception {
  JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
  DiagnosticCollector<JavaFileObject> diagnostics=new DiagnosticCollector<>();
  try(StandardJavaFileManager fm=compiler.getStandardFileManager(diagnostics,null,null)) {
   List<String> files=Files.readAllLines(Path.of(args[0]));
   var units=fm.getJavaFileObjectsFromStrings(files);
   var opts=List.of("-proc:none","-implicit:none","-classpath",args[1],"-sourcepath",args[2],"-Xmaxerrs","10000");
   JavacTask task=(JavacTask)compiler.getTask(null,fm,diagnostics,opts,null,units);
   List<CompilationUnitTree> parsed=new ArrayList<>(); for(var u:task.parse())parsed.add(u);
   try {task.analyze();} catch (RuntimeException ex) {System.err.println("ATTRIBUTION: "+ex);}
   Trees trees=Trees.instance(task);
   for(var unit:parsed) new TreePathScanner<Void,Void>() {
    void record(Tree tree, String kind) {
     TreePath p=getCurrentPath(); Element e=trees.getElement(p); ExecutableElement method=e instanceof ExecutableElement?(ExecutableElement)e:null;
     boolean resolved=method!=null && method.getEnclosingElement() instanceof TypeElement && method.asType().getKind()!=javax.lang.model.type.TypeKind.ERROR;
     String owner=resolved?((TypeElement)method.getEnclosingElement()).getQualifiedName().toString():null;
     long start=trees.getSourcePositions().getStartPosition(unit,tree); long line=start<0?-1:unit.getLineMap().getLineNumber(start);
     String context=null; TreePath t=p; while(t!=null) {if(t.getLeaf() instanceof StatementTree){context=t.getLeaf().toString();break;}t=t.getParentPath();}
     System.out.println("{\"file\":"+q(Path.of(unit.getSourceFile().toUri()).toString())+",\"line\":"+line+",\"kind\":"+q(kind)+",\"expression\":"+q(tree.toString())+",\"owner\":"+q(owner)+",\"signature\":"+q(resolved?method.toString():null)+",\"resolved\":"+resolved+",\"statement\":"+q(context)+"}");
    }
    public Void visitMethodInvocation(MethodInvocationTree n,Void v){record(n,"method_invocation");return super.visitMethodInvocation(n,v);}
    public Void visitNewClass(NewClassTree n,Void v){record(n,"constructor");return super.visitNewClass(n,v);}
    public Void visitMemberReference(MemberReferenceTree n,Void v){record(n,"method_reference");return super.visitMemberReference(n,v);}
   }.scan(unit,null);
   long errors=diagnostics.getDiagnostics().stream().filter(d->d.getKind()==Diagnostic.Kind.ERROR).count();
   System.err.println("files="+files.size()+" compiler_errors="+errors);
   diagnostics.getDiagnostics().stream().filter(d->d.getKind()==Diagnostic.Kind.ERROR).limit(10).forEach(d->System.err.println(d));
  }
 }
}
